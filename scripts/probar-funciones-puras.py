#!/usr/bin/env python3
"""
Unit tests for the pure (MLX-free) logic of the MLX server.

These exercise the fragile bits — tool-call parsing/recovery, response
cleaning, Anthropic message conversion and session-mode detection — WITHOUT
loading a model or MLX. Run with any Python 3:

    python3 scripts/probar-funciones-puras.py

(The end-to-end HTTP test that needs a running server lives in
 scripts/probar-servidor-mlx.py.)
"""

import os
import sys
import unittest

# Make the `mlx_server` package (in proxy/) importable.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "proxy"))

from mlx_server.tool_calls import (
    convert_tools_for_llm,
    format_tools_as_text,
    recover_garbled_tool_json,
    parse_tool_calls,
)
from mlx_server.text_cleaning import strip_think_tags, clean_response
from mlx_server.messages import convert_messages, tokenize_messages
from mlx_server.modes import (
    looks_like_code_session,
    optimize_for_code,
    looks_like_claude_code_browser_session,
    optimize_for_browser,
    CODE_SYSTEM_PROMPT,
    BROWSER_SYSTEM_PROMPT,
)
from mlx_server import metrics


class TestParseToolCalls(unittest.TestCase):
    def test_hf_json_format(self):
        text = '<tool_call>{"name": "Bash", "arguments": {"command": "ls -la"}}</tool_call>'
        calls, remaining = parse_tool_calls(text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["name"], "Bash")
        self.assertEqual(calls[0]["arguments"], {"command": "ls -la"})
        self.assertEqual(remaining, "")

    def test_gemma4_native_format(self):
        text = '<|tool_call>call:Bash{command:<|"|>ls -la<|"|>}<tool_call|>'
        calls, remaining = parse_tool_calls(text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["name"], "Bash")
        self.assertEqual(calls[0]["arguments"], {"command": "ls -la"})

    def test_llama_raw_json_format(self):
        text = 'Let me check.\n{"type":"function","name":"Read","parameters":{"file_path":"/etc/hosts"}}'
        calls, remaining = parse_tool_calls(text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["name"], "Read")
        self.assertEqual(calls[0]["arguments"], {"file_path": "/etc/hosts"})
        self.assertIn("Let me check", remaining)

    def test_function_parameter_format(self):
        text = '<function=Bash><parameter=command>echo hi</parameter></function>'
        calls, remaining = parse_tool_calls(text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["name"], "Bash")
        self.assertEqual(calls[0]["arguments"], {"command": "echo hi"})

    def test_garbled_recovery_inside_tool_call(self):
        # Hybrid XML/JSON garble that json.loads can't parse
        text = '<tool_call>{"name": "Bash", "parameter=command>echo hi</parameter>}</tool_call>'
        calls, remaining = parse_tool_calls(text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["name"], "Bash")
        self.assertEqual(calls[0]["arguments"].get("command"), "echo hi")

    def test_plain_text_no_tools(self):
        text = "Hello! How can I help you today?"
        calls, remaining = parse_tool_calls(text)
        self.assertEqual(calls, [])
        self.assertEqual(remaining, "Hello! How can I help you today?")

    def test_dedup_same_tool(self):
        # Same call emitted twice -> deduped by name
        text = ('<tool_call>{"name": "Bash", "arguments": {"command": "ls"}}</tool_call>'
                '<tool_call>{"name": "Bash", "arguments": {"command": "ls"}}</tool_call>')
        calls, _ = parse_tool_calls(text)
        self.assertEqual(len(calls), 1)

    def test_text_preserved_before_tool_call(self):
        text = 'Sure, listing now.\n<tool_call>{"name": "Bash", "arguments": {"command": "ls"}}</tool_call>'
        calls, remaining = parse_tool_calls(text)
        self.assertEqual(len(calls), 1)
        self.assertIn("Sure, listing now.", remaining)


class TestRecoverGarbled(unittest.TestCase):
    def test_no_name_returns_none(self):
        self.assertIsNone(recover_garbled_tool_json('{"arguments": {}}'))

    def test_parameter_equals_pattern(self):
        out = recover_garbled_tool_json('{"name": "Edit", "parameter=file_path>/a/b.txt</parameter>')
        self.assertIsNotNone(out)
        self.assertEqual(out["name"], "Edit")
        self.assertEqual(out["arguments"].get("file_path"), "/a/b.txt")

    def test_single_arg_tool_fallback(self):
        out = recover_garbled_tool_json('{"name": "Bash", "command is broken here xyz')
        self.assertIsNotNone(out)
        self.assertEqual(out["name"], "Bash")
        self.assertIn("command", out["arguments"])


class TestTextCleaning(unittest.TestCase):
    def test_strip_think_tags(self):
        self.assertEqual(strip_think_tags("<think>reasoning</think>Hello"), "Hello")

    def test_strip_gemma_channel_thought(self):
        self.assertEqual(
            strip_think_tags("<|channel>thought\nhmm<channel|>Answer"), "Answer"
        )

    def test_strip_returns_original_if_empty_after_strip(self):
        # If stripping leaves nothing, original is returned (avoid empty output)
        self.assertEqual(strip_think_tags("<think>only thoughts</think>"), "<think>only thoughts</think>")

    def test_clean_truncates_at_turn_marker(self):
        self.assertEqual(clean_response("Answer text<turn|>garbage after"), "Answer text")

    def test_clean_strips_python_tag(self):
        self.assertEqual(clean_response("<|python_tag|>do it"), "do it")


class TestConvertMessages(unittest.TestCase):
    def test_system_and_string_content(self):
        body = {"system": "sys", "messages": [{"role": "user", "content": "hi"}]}
        msgs = convert_messages(body)
        self.assertEqual(msgs[0], {"role": "system", "content": "sys"})
        self.assertEqual(msgs[1], {"role": "user", "content": "hi"})

    def test_system_as_block_list(self):
        body = {"system": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}],
                "messages": []}
        msgs = convert_messages(body)
        self.assertEqual(msgs[0], {"role": "system", "content": "a\nb"})

    def test_assistant_tool_use_to_tool_call(self):
        body = {"messages": [{
            "role": "assistant",
            "content": [{"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}],
        }]}
        msgs = convert_messages(body)
        self.assertEqual(msgs[0]["role"], "assistant")
        self.assertIn("<tool_call>", msgs[0]["content"])
        self.assertIn('"name": "Bash"', msgs[0]["content"])

    def test_tool_result_to_tool_role(self):
        body = {"messages": [{
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "x", "content": "output text"}],
        }]}
        msgs = convert_messages(body)
        self.assertEqual(msgs[0], {"role": "tool", "content": "output text"})

    def test_tool_result_content_as_list(self):
        body = {"messages": [{
            "role": "user",
            "content": [{"type": "tool_result", "content": [{"type": "text", "text": "line"}]}],
        }]}
        msgs = convert_messages(body)
        self.assertEqual(msgs[0]["role"], "tool")
        self.assertIn("line", msgs[0]["content"])


class TestConvertTools(unittest.TestCase):
    def test_shape(self):
        out = convert_tools_for_llm([
            {"name": "Bash", "description": "run", "input_schema": {"type": "object"}}
        ])
        self.assertEqual(out[0]["type"], "function")
        self.assertEqual(out[0]["function"]["name"], "Bash")
        self.assertEqual(out[0]["function"]["description"], "run")

    def test_empty_returns_none(self):
        self.assertIsNone(convert_tools_for_llm([]))

    def test_format_as_text_lists_tools(self):
        text = format_tools_as_text([
            {"function": {"name": "Bash", "description": "run", "parameters": {
                "properties": {"command": {"type": "string", "description": "cmd"}},
                "required": ["command"]}}}
        ])
        self.assertIn("## Bash", text)
        self.assertIn("command", text)
        self.assertIn("(required)", text)


class TestModes(unittest.TestCase):
    def test_detect_code_session(self):
        self.assertTrue(looks_like_code_session({"tools": [{"name": "Bash"}]}))
        self.assertFalse(looks_like_code_session({"tools": [{"name": "Whatever"}]}))

    def test_optimize_for_code_filters_and_swaps_prompt(self):
        body = {"system": "huge harness prompt", "tools": [{"name": "Bash"}, {"name": "Other"}]}
        out = optimize_for_code(body)
        self.assertEqual(out["system"], CODE_SYSTEM_PROMPT)
        names = {t["name"] for t in out["tools"]}
        self.assertEqual(names, {"Bash"})

    def test_detect_browser_session(self):
        self.assertTrue(looks_like_claude_code_browser_session(
            {"tools": [{"name": "mcp__chrome-devtools__take_snapshot"}]}))
        self.assertFalse(looks_like_claude_code_browser_session(
            {"tools": [{"name": "Bash"}]}))

    def test_browser_passthrough_for_direct_client(self):
        # No chrome-devtools tools -> untouched (don't clobber direct clients)
        body = {"system": "mine", "tools": []}
        out = optimize_for_browser(body)
        self.assertEqual(out["system"], "mine")

    def test_browser_optimizes_real_session(self):
        body = {"system": "huge", "tools": [
            {"name": "mcp__chrome-devtools__take_snapshot"},
            {"name": "mcp__chrome-devtools__click"},
            {"name": "Bash"},
        ]}
        out = optimize_for_browser(body)
        self.assertEqual(out["system"], BROWSER_SYSTEM_PROMPT)
        self.assertTrue(all(t["name"].startswith("mcp__chrome-devtools__") for t in out["tools"]))


class _FakeTokenizer:
    """Minimal tokenizer stand-in for tokenize_messages tests."""
    def __init__(self, supports_tools=True, template_works=True):
        self.supports_tools = supports_tools
        self.template_works = template_works
        self.last_messages = None

    def apply_chat_template(self, messages, **kwargs):
        if not self.template_works:
            raise RuntimeError("no template")
        if "tools" in kwargs and not self.supports_tools:
            raise TypeError("unexpected 'tools' kwarg")
        self.last_messages = messages
        return [1, 2, 3]

    def encode(self, text):
        return [9, 9]


class TestTokenizeMessages(unittest.TestCase):
    def test_success_path_with_tools(self):
        tok = _FakeTokenizer(supports_tools=True)
        out = tokenize_messages(tok, [{"role": "user", "content": "hi"}], tools=[{"x": 1}])
        self.assertEqual(out, [1, 2, 3])

    def test_falls_back_to_system_injection(self):
        # Template rejects the tools kwarg -> retried with tools text in system prompt
        tok = _FakeTokenizer(supports_tools=False, template_works=True)
        msgs = [{"role": "system", "content": "base"}, {"role": "user", "content": "hi"}]
        out = tokenize_messages(tok, msgs, tools=[
            {"function": {"name": "Bash", "description": "", "parameters": {}}}])
        self.assertEqual(out, [1, 2, 3])
        # The retry injected tool text into the system message
        self.assertIn("Available Tools", tok.last_messages[0]["content"])

    def test_plain_text_fallback(self):
        tok = _FakeTokenizer(template_works=False)
        out = tokenize_messages(tok, [{"role": "user", "content": "hi"}], tools=None)
        self.assertEqual(out, [9, 9])


class TestMetrics(unittest.TestCase):
    def setUp(self):
        metrics.reset()

    def test_record_request_aggregates(self):
        metrics.record_request({
            "prompt_tokens": 100, "output_tokens": 20, "elapsed": 2.0, "tps": 10.0,
            "finish_reason": "tool_use", "mode": "code", "tools": ["Bash", "Read"],
            "retries": 1, "cache_hit": True,
        })
        snap = metrics.snapshot()
        self.assertEqual(snap["total_requests"], 1)
        self.assertEqual(snap["total_prompt_tokens"], 100)
        self.assertEqual(snap["total_output_tokens"], 20)
        self.assertEqual(snap["tool_calls_total"], 2)
        self.assertEqual(snap["tool_calls_by_name"], {"Bash": 1, "Read": 1})
        self.assertEqual(snap["retries_total"], 1)
        self.assertEqual(snap["cache_hits"], 1)
        self.assertEqual(snap["avg_tps"], 10.0)  # 20 tokens / 2.0 s
        self.assertEqual(len(snap["recent"]), 1)

    def test_cache_hit_rate(self):
        metrics.record_request({"cache_hit": True})
        metrics.record_request({"cache_hit": False})
        metrics.record_request({"cache_hit": True})
        snap = metrics.snapshot()
        self.assertEqual(snap["cache_hits"], 2)
        self.assertEqual(snap["cache_misses"], 1)
        self.assertAlmostEqual(snap["cache_hit_rate"], round(2/3, 3))

    def test_record_error(self):
        metrics.record_error("boom")
        snap = metrics.snapshot()
        self.assertEqual(snap["total_requests"], 1)
        self.assertEqual(snap["total_errors"], 1)
        self.assertEqual(snap["last_error"], "boom")
        self.assertFalse(snap["recent"][0]["ok"])

    def test_note_recovery(self):
        metrics.note_recovery("Bash")
        metrics.note_recovery("Bash")
        metrics.note_recovery("Edit")
        snap = metrics.snapshot()
        self.assertEqual(snap["recoveries_total"], 3)
        self.assertEqual(snap["recoveries_by_name"], {"Bash": 2, "Edit": 1})

    def test_inflight_never_negative(self):
        metrics.inc_inflight()
        metrics.dec_inflight()
        metrics.dec_inflight()  # extra dec should not go below zero
        self.assertEqual(metrics.snapshot()["in_flight"], 0)

    def test_recent_ring_buffer_bounded(self):
        for i in range(metrics.RECENT_MAXLEN + 20):
            metrics.record_request({"output_tokens": 1})
        snap = metrics.snapshot()
        self.assertEqual(len(snap["recent"]), metrics.RECENT_MAXLEN)
        # total_requests keeps counting beyond the ring buffer size
        self.assertEqual(snap["total_requests"], metrics.RECENT_MAXLEN + 20)

    def test_snapshot_is_json_serializable(self):
        import json as _json
        metrics.record_request({"tools": ["Bash"], "mode": "code"})
        metrics.note_recovery("Read")
        _json.dumps(metrics.snapshot())  # must not raise


if __name__ == "__main__":
    unittest.main(verbosity=2)
