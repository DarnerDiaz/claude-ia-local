"""Inference pipeline: mode optimization → tokenize → generate → parse tools.

Owns the prompt cache (KV reuse across requests) and the tool-call retry loop.
Imports MLX, so it is NOT safe to import in pure unit tests — the pure logic it
orchestrates (parsing, conversion, modes) lives in importable, MLX-free modules.
"""

import os
import time
import threading
import uuid

from mlx_lm.generate import stream_generate
from mlx_lm.sample_utils import make_sampler
from mlx_lm.models.cache import make_prompt_cache, RotatingKVCache

from . import config, model_loader, metrics
from .config import log
from .text_cleaning import clean_response
from .tool_calls import convert_tools_for_llm, parse_tool_calls
from .messages import convert_messages, tokenize_messages
from .modes import optimize_for_browser, looks_like_code_session, optimize_for_code

# ─── Globals ─────────────────────────────────────────────────────────────────

generate_lock = threading.Lock()
# Prompt cache: reuse KV state across requests to avoid re-prefilling system+tools
_prompt_cache = None
_cached_token_prefix = None  # token IDs we've already prefilled
_first_request = True


def generate_response(body):
    """Run MLX inference and return Anthropic-formatted response."""
    global _first_request

    # In browser mode, strip Claude Code bloat before inference.
    # Otherwise, auto-detect Claude Code coding sessions and apply code mode.
    mode = "plain"
    if config.BROWSER_MODE:
        body = optimize_for_browser(body)
        mode = "browser"
    elif config.CODE_MODE_ENABLED and looks_like_code_session(body):
        body = optimize_for_code(body)
        mode = "code"

    # Opt-in: append a project-specific system prompt to whatever the
    # current mode produced. Used by Narrative Gemma to inject narration
    # rules without rewriting the whole code/browser prompt.
    extra_path = os.environ.get("MLX_APPEND_SYSTEM_PROMPT_FILE")
    if extra_path and os.path.exists(extra_path):
        try:
            with open(extra_path) as ef:
                extra = ef.read().strip()
            if extra:
                current = body.get("system", "")
                if isinstance(current, list):
                    body["system"] = current + [
                        {"type": "text", "text": "\n\n---\n\n" + extra}
                    ]
                else:
                    body["system"] = (current or "") + "\n\n---\n\n" + extra
                log(f"  Appended {len(extra)} chars from MLX_APPEND_SYSTEM_PROMPT_FILE")
        except Exception as _e:
            log(f"  Failed to append extra system prompt: {_e}")

    if _first_request:
        _first_request = False
        # Dump tool names and system prompt length for debugging
        tools = body.get("tools", [])
        tool_names = [t.get("name", "?") for t in tools]
        sys_prompt = body.get("system", "")
        if isinstance(sys_prompt, list):
            sys_len = sum(len(b.get("text", "")) for b in sys_prompt)
        else:
            sys_len = len(sys_prompt)
        log(f"  [FIRST REQUEST] tools={len(tools)} names={tool_names}")
        log(f"  [FIRST REQUEST] system_prompt_len={sys_len}")
        # Dump first 500 chars of system prompt to see if MCP tools are described there
        sys_text = sys_prompt if isinstance(sys_prompt, str) else str(sys_prompt)[:500]
        log(f"  [FIRST REQUEST] system_start={sys_text[:300]}")

    # Convert tools from Anthropic → MLX format
    anthropic_tools = body.get("tools", [])
    llm_tools = convert_tools_for_llm(anthropic_tools) if anthropic_tools else None

    messages = convert_messages(body)
    max_tokens = body.get("max_tokens", config.DEFAULT_MAX_TOKENS)
    temperature = body.get("temperature", 0.2)

    if llm_tools:
        log(f"  Tools: {len(llm_tools)} ({', '.join(t['function']['name'] for t in llm_tools[:5])}{'...' if len(llm_tools) > 5 else ''})")

    # Tokenize (with tools if present)
    token_ids = tokenize_messages(model_loader.tokenizer, messages, tools=llm_tools)
    prompt_tokens = len(token_ids)
    log(f"  Prompt: {prompt_tokens} tokens")

    # ─── Prompt cache: reuse KV for shared prefix tokens ───
    global _prompt_cache, _cached_token_prefix

    # Check if cache type supports safe trim+reuse (standard KVCache only,
    # RotatingKVCache from Gemma 4 has a circular buffer that breaks on trim+extend)
    cache_is_safe = _prompt_cache is not None and not isinstance(_prompt_cache[0], RotatingKVCache)

    # Find how many leading tokens match the previous request's prompt
    cache_hit_len = 0
    if cache_is_safe and _cached_token_prefix is not None:
        max_check = min(len(token_ids), len(_cached_token_prefix))
        for i in range(max_check):
            if token_ids[i] == _cached_token_prefix[i]:
                cache_hit_len = i + 1
            else:
                break

    # Always leave at least 1 token to prefill — mlx_lm.stream_generate raises
    # ValueError if the prompt is empty (happens when new prompt == cached prefix)
    if cache_hit_len >= len(token_ids):
        cache_hit_len = len(token_ids) - 1

    if cache_hit_len > 0:
        # Trim cache back to the shared prefix, then only prefill the delta
        #cache_offset = _prompt_cache[0].offset  # total tokens in cache (prompt + gen)
        # Try .step instead of .offset
        cache_offset = _prompt_cache[0].step if hasattr(_prompt_cache[0], 'step') else 0
        trim_amount = cache_offset - cache_hit_len
        if trim_amount > 0:
            for c in _prompt_cache:
                c.trim(trim_amount)
        delta_tokens = token_ids[cache_hit_len:]
        new_tokens = len(delta_tokens)
        log(f"  Cache hit: {cache_hit_len} reused, {new_tokens} new tokens to prefill (saved {cache_hit_len} tokens)")
        # Feed only the new tokens, with the existing cache
        prompt_for_gen = delta_tokens
    else:
        if _prompt_cache is not None and isinstance(_prompt_cache[0], RotatingKVCache):
            log(f"  RotatingKVCache: fresh cache each request (no trim support)")
        else:
            log(f"  Cache miss: full prefill of {prompt_tokens} tokens")
        _prompt_cache = None
        prompt_for_gen = token_ids

    cache_hit = cache_hit_len > 0

    # Build generation kwargs — always pass a prompt_cache so we can reuse it
    if _prompt_cache is None:
        _prompt_cache = make_prompt_cache(model_loader.model)
        log(f"  Created new prompt cache ({len(_prompt_cache)} layers)")
    gen_kwargs = {
        "prefill_step_size": config.PREFILL_SIZE,
        "prompt_cache": _prompt_cache,
    }
    if config.KV_BITS:
        gen_kwargs["kv_bits"] = config.KV_BITS
        gen_kwargs["kv_group_size"] = 64
        gen_kwargs["quantized_kv_start"] = config.KV_QUANT_START

    if temperature > 0:
        gen_kwargs["sampler"] = make_sampler(temp=temperature)
    else:
        gen_kwargs["sampler"] = make_sampler(temp=0.0)

    # Generate
    full_text = ""
    gen_tokens = 0
    finish_reason = "end_turn"
    t0 = time.time()

    with generate_lock:
        for response in stream_generate(
            model=model_loader.model,
            tokenizer=model_loader.tokenizer,
            prompt=prompt_for_gen,
            max_tokens=max_tokens,
            **gen_kwargs,
        ):
            full_text += response.text
            gen_tokens = response.generation_tokens
            if response.finish_reason == "length":
                finish_reason = "max_tokens"
            elif response.finish_reason == "stop":
                finish_reason = "end_turn"

    # Cache is updated in-place by MLX — save the token prefix for next request's diff
    _cached_token_prefix = token_ids

    elapsed = time.time() - t0
    tps = gen_tokens / elapsed if elapsed > 0 else 0
    log(f"  Generated: {gen_tokens} tokens in {elapsed:.1f}s ({tps:.1f} tok/s)")

    # Clean output (preserves <tool_call> tags)
    text = clean_response(full_text)

    # Parse tool calls from model output
    tool_calls, remaining_text = parse_tool_calls(text)

    # ─── Retry logic: if model expressed intent to use a tool but we got no valid calls ───
    tool_intent_phrases = [
        "here's the command", "bash(", "read(", "edit(", "write(",
        "<tool_call>", "<function=",
    ]
    retries_used = 0
    if not tool_calls and any(p in remaining_text.lower() for p in tool_intent_phrases):
        for retry in range(config.MAX_TOOL_RETRIES):
            retries_used += 1
            log(f"  Retry {retry+1}/{config.MAX_TOOL_RETRIES}: tool intent detected but no valid tool call, re-prompting")
            retry_messages = messages + [
                {"role": "assistant", "content": full_text},
                {"role": "user", "content": (
                    "Your previous response tried to call a tool but the format was wrong. "
                    "Please call the tool now using EXACTLY this format:\n"
                    '<tool_call>\n{"name": "TOOL_NAME", "arguments": {"param": "value"}}\n</tool_call>\n'
                    "Do NOT use <parameter=...> tags inside tool_call. Use pure JSON with \"arguments\" key."
                )}
            ]
            retry_tokens = tokenize_messages(model_loader.tokenizer, retry_messages, tools=llm_tools)
            log(f"  Retry prompt: {len(retry_tokens)} tokens")

            retry_text = ""
            retry_gen = 0
            with generate_lock:
                for response in stream_generate(
                    model=model_loader.model, tokenizer=model_loader.tokenizer, prompt=retry_tokens,
                    max_tokens=max_tokens, **gen_kwargs,
                ):
                    retry_text += response.text
                    retry_gen = response.generation_tokens

            retry_text = clean_response(retry_text)
            retry_calls, retry_remaining = parse_tool_calls(retry_text)
            gen_tokens += retry_gen

            if retry_calls:
                tool_calls = retry_calls
                # Preserve original reasoning text, not retry text
                log(f"  Retry succeeded: {', '.join(tc['name'] for tc in retry_calls)}")
                break
            else:
                log(f"  Retry {retry+1} failed, still no valid tool call")

    # Build content blocks
    content_blocks = []

    if remaining_text.strip():
        content_blocks.append({"type": "text", "text": remaining_text.strip()})

    if tool_calls:
        # If we have tool calls but no text, add empty text block (Anthropic requires at least one)
        if not content_blocks:
            content_blocks.append({"type": "text", "text": ""})

        for tc in tool_calls:
            tool_id = f"toolu_{uuid.uuid4().hex[:24]}"
            content_blocks.append({
                "type": "tool_use",
                "id": tool_id,
                "name": tc["name"],
                "input": tc["arguments"],
            })
        finish_reason = "tool_use"
        log(f"  Tool calls: {', '.join(tc['name'] for tc in tool_calls)}")

    if not content_blocks:
        content_blocks.append({"type": "text", "text": "(No output)"})

    # Record metrics for the dashboard (fire-and-forget).
    metrics.record_request({
        "prompt_tokens": prompt_tokens,
        "output_tokens": gen_tokens,
        "elapsed": elapsed,
        "tps": tps,
        "finish_reason": finish_reason,
        "mode": mode,
        "tools": [tc["name"] for tc in tool_calls],
        "retries": retries_used,
        "cache_hit": cache_hit,
    })

    return {
        "id": f"msg_{uuid.uuid4().hex[:24]}",
        "type": "message",
        "role": "assistant",
        "model": body.get("model", "claude-sonnet-4-6"),
        "content": content_blocks,
        "stop_reason": finish_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": prompt_tokens,
            "output_tokens": gen_tokens,
        }
    }
