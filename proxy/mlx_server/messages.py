"""Anthropic Messages format <-> MLX chat messages, plus tokenization.

Pure functions — no MLX dependency. `tokenize_messages` takes the tokenizer as
an explicit argument (rather than reaching for a module global) so it can be
exercised with a fake tokenizer in tests.
"""

import json

from .config import log
from .tool_calls import format_tools_as_text


def convert_messages(body):
    """Convert Anthropic Messages format to MLX chat messages.

    Handles:
    - Text messages (passthrough)
    - Assistant messages with tool_use blocks → <tool_call> format
    - User messages with tool_result blocks → role="tool" messages
    """
    messages = []

    # System prompt
    if body.get("system"):
        sys_text = body["system"]
        if isinstance(sys_text, list):
            sys_text = "\n".join(b.get("text", "") for b in sys_text if b.get("type") == "text")
        messages.append({"role": "system", "content": sys_text})

    # Conversation messages
    for msg in body.get("messages", []):
        role = msg.get("role", "user")
        content = msg.get("content", "")

        # Simple string content
        if isinstance(content, str):
            messages.append({"role": role, "content": content})
            continue

        # List of content blocks
        if isinstance(content, list):
            text_parts = []
            tool_use_parts = []
            tool_result_parts = []

            for block in content:
                btype = block.get("type", "")
                if btype == "text":
                    text_parts.append(block.get("text", ""))
                elif btype == "tool_use":
                    tool_use_parts.append(block)
                elif btype == "tool_result":
                    tool_result_parts.append(block)

            # Assistant message with tool_use blocks → convert to LLM format
            if role == "assistant" and tool_use_parts:
                content_str = ""
                if text_parts:
                    content_str = "\n".join(p for p in text_parts if p)
                for tu in tool_use_parts:
                    call_json = json.dumps({
                        "name": tu.get("name", ""),
                        "arguments": tu.get("input", {})
                    }, ensure_ascii=False)
                    content_str += f"\n<tool_call>\n{call_json}\n</tool_call>"
                messages.append({"role": "assistant", "content": content_str.strip()})

            # User message with tool_result blocks → split into tool messages
            elif tool_result_parts:
                # Add any text from the user first
                if text_parts:
                    text = "\n".join(p for p in text_parts if p)
                    if text.strip():
                        messages.append({"role": "user", "content": text})

                # Each tool_result becomes a "tool" role message
                for tr in tool_result_parts:
                    result_content = tr.get("content", "")
                    if isinstance(result_content, list):
                        result_content = "\n".join(
                            b.get("text", str(b)) for b in result_content
                        )
                    elif not isinstance(result_content, str):
                        result_content = str(result_content)
                    # Include tool name context if we can find it
                    messages.append({"role": "tool", "content": result_content})

            # Regular message with just text
            else:
                text = "\n".join(p for p in text_parts if p)
                if text.strip():
                    messages.append({"role": role, "content": text})

    return messages


def tokenize_messages(tokenizer, messages, tools=None):
    """Apply chat template and tokenize, with optional tool definitions."""
    kwargs = {
        "add_generation_prompt": True,
        "tokenize": True,
    }
    if tools:
        kwargs["tools"] = tools

    try:
        token_ids = tokenizer.apply_chat_template(messages, **kwargs)
        if tools:
            log(f"  Tools: {len(tools)} tools passed via chat template")
        return token_ids
    except (TypeError, Exception) as e:
        # If tools param failed, try injecting into system prompt instead
        if tools:
            log(f"  Chat template tools param failed ({e}), injecting into system prompt")
            tool_text = format_tools_as_text(tools)
            msg_copy = [m.copy() for m in messages]
            if msg_copy and msg_copy[0]["role"] == "system":
                msg_copy[0]["content"] = msg_copy[0]["content"] + "\n\n" + tool_text
            else:
                msg_copy.insert(0, {"role": "system", "content": tool_text})

            try:
                return tokenizer.apply_chat_template(
                    msg_copy, add_generation_prompt=True, tokenize=True
                )
            except Exception:
                pass

        # Final fallback: plain text
        log("  Warning: using plain text fallback for tokenization")
        text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        text += "\nassistant: "
        return tokenizer.encode(text)
