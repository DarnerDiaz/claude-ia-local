"""Tool-call conversion and parsing.

Converts Anthropic tool definitions to the model's native function-calling
format, and parses tool calls back out of generated text. Local models emit
tool calls in several (often malformed) shapes — Gemma 4 native, Llama raw
JSON, HuggingFace <tool_call>, <function=...>, and assorted garble — so the
parser tries many formats and includes recovery heuristics.

Pure functions — no MLX dependency.
"""

import json
import re

from .config import log
from .metrics import note_recovery


def convert_tools_for_llm(anthropic_tools):
    """Convert Anthropic tool definitions to HuggingFace/Llama format."""
    if not anthropic_tools:
        return None
    llm_tools = []
    for tool in anthropic_tools:
        llm_tools.append({
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
            }
        })
    return llm_tools


def format_tools_as_text(tools):
    """Format tools as text for system prompt (fallback if chat template doesn't support tools param)."""
    lines = ["# Available Tools\n"]
    lines.append("CRITICAL: You MUST call tools using EXACTLY this JSON format inside <tool_call> tags:")
    lines.append("")
    lines.append('<tool_call>')
    lines.append('{"name": "Bash", "arguments": {"command": "ls -la"}}')
    lines.append('</tool_call>')
    lines.append("")
    lines.append("RULES:")
    lines.append('- The content inside <tool_call> MUST be valid JSON with "name" and "arguments" keys')
    lines.append('- Do NOT use <parameter=...> tags inside <tool_call> — use the "arguments" JSON object')
    lines.append('- Do NOT mix XML and JSON — use ONLY pure JSON inside the tags')
    lines.append("- You may call multiple tools by using multiple <tool_call> blocks")
    lines.append("- Output any reasoning text BEFORE the tool calls, not inside them")
    lines.append("")
    for tool in tools:
        func = tool.get("function", tool)
        name = func.get("name", "")
        desc = func.get("description", "")
        params = func.get("parameters", {})
        lines.append(f"## {name}")
        if desc:
            lines.append(f"{desc}")
        props = params.get("properties", {})
        required = params.get("required", [])
        if props:
            for pname, pdef in props.items():
                req = " (required)" if pname in required else ""
                ptype = pdef.get("type", "any")
                pdesc = pdef.get("description", "")
                lines.append(f"  - {pname}: {ptype}{req} — {pdesc}")
        lines.append("")
    return "\n".join(lines)


def recover_garbled_tool_json(content, original_text=""):
    """Attempt to recover tool name and arguments from garbled JSON inside <tool_call> tags.

    Models sometimes produce hybrid XML/JSON like:
      {"name": "Bash", "parameter=command>cd ~/Desktop && rm -rf ...
      {"name": "Bash", "<parameter_commands>["rm -rf ...
      {"name": "Edit", "parameter=file_path>/some/path</parameter...
    """
    # Extract tool name
    name_match = re.search(r'"name"\s*:\s*"([^"]+)"', content)
    if not name_match:
        return None
    tool_name = name_match.group(1)

    arguments = {}

    # Pattern A: "parameter=key>value" (most common garble)
    # Matches: "parameter=command>cd ~/Desktop..." or parameter=command>value</parameter>
    param_a = re.finditer(r'["\s,]?parameter=(\w+)>\s*(.*?)(?:</parameter>|$)', content, re.DOTALL)
    for m in param_a:
        key = m.group(1)
        val = m.group(2).strip().rstrip('"}\n')
        if val:
            arguments[key] = val

    # Pattern B: "<parameter_key>value" or "<parameter_key>["value"]"
    if not arguments:
        param_b = re.finditer(r'<parameter[_=](\w+)>\s*(.*?)(?:</parameter|<|$)', content, re.DOTALL)
        for m in param_b:
            key = m.group(1)
            val = m.group(2).strip().strip('[]"')
            if val:
                arguments[key] = val

    # Pattern C: "arguments" key exists but is malformed — try to extract the value after it
    if not arguments:
        args_match = re.search(r'"arguments"\s*:\s*\{(.*)', content, re.DOTALL)
        if args_match:
            raw = args_match.group(1)
            # Try to find key-value pairs
            kv_matches = re.finditer(r'"(\w+)"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
            for m in kv_matches:
                arguments[m.group(1)] = m.group(2)

    # Pattern D: single-argument tools — if we have a tool name and leftover text, use it
    # Common for Bash (command), Read (file_path), etc.
    if not arguments:
        single_arg_tools = {
            "Bash": "command", "Read": "file_path", "Write": "file_path",
            "Glob": "pattern", "Grep": "pattern",
        }
        if tool_name in single_arg_tools:
            # Everything after the tool name declaration is likely the argument value
            after_name = content[name_match.end():]
            # Strip JSON noise
            val = re.sub(r'^[\s,":{}]+', '', after_name)
            val = re.sub(r'[\s"}]+$', '', val)
            # Remove parameter= prefix if present
            val = re.sub(r'^parameter=\w+>\s*', '', val)
            val = re.sub(r'^<parameter[_=]\w+>\s*', '', val)
            if val and len(val) > 2:
                arguments[single_arg_tools[tool_name]] = val

    if arguments:
        log(f"  Recovered garbled tool call: {tool_name} with {list(arguments.keys())}")
        note_recovery(tool_name)
        return {"name": tool_name, "arguments": arguments}

    return None


def parse_tool_calls(text):
    """Parse tool calls from generated text. Handles multiple formats including
    Gemma 4 native format. Returns (list of tool calls, remaining text).
    """
    tool_calls = []

    # Format 0: Gemma 4 native — <|tool_call>call:Name{key:<|"|>val<|"|>}<tool_call|>
    # Parse BEFORE replacing escape tokens — use <|"|> as reliable value delimiters
    gemma4_pattern = r'<\|tool_call>(.*?)<tool_call\|>'
    gemma4_matches = list(re.finditer(gemma4_pattern, text, re.DOTALL))
    if gemma4_matches:
        remaining = text
        for match in gemma4_matches:
            remaining = remaining.replace(match.group(0), "", 1)
            content = match.group(1).strip()
            name_m = re.match(r'call:([\w.]+)\{(.*)\}', content, re.DOTALL)
            if not name_m:
                log(f"  Gemma4 no name match: {content[:80]}")
                continue
            name = name_m.group(1)
            args_str = name_m.group(2)
            arguments = {}
            # Primary: extract key:<|"|>value<|"|> pairs (handles embedded quotes)
            for km in re.finditer(r'(\w+):<\|"\|>(.*?)<\|"\|>', args_str, re.DOTALL):
                arguments[km.group(1)] = km.group(2)
            # Fallback: unquoted values (numbers, simple strings)
            if not arguments:
                for km in re.finditer(r'(\w+):([^,}]+)', args_str):
                    val = km.group(2).strip().strip('"\'')
                    arguments[km.group(1)] = val
            if arguments:
                tool_calls.append({"name": name, "arguments": arguments})
                log(f"  Gemma4 tool call: {name}({list(arguments.keys())})")
            else:
                log(f"  Gemma4 no args parsed: {content[:80]}")
        if tool_calls:
            return tool_calls, remaining.strip()

    remaining = text

    # Format 0.5: Llama 3.3 raw JSON — {"type":"function","name":"...","parameters":{...}}
    # Use json.JSONDecoder.raw_decode for robust nested JSON parsing
    _decoder = json.JSONDecoder()
    _pos = 0
    while _pos < len(text):
        idx = text.find('{"type"', _pos)
        if idx == -1:
            break
        try:
            obj, end_pos = _decoder.raw_decode(text, idx)
            if obj.get("type") == "function" and "name" in obj:
                name = obj["name"]
                arguments = obj.get("parameters", {})
                tool_calls.append({"name": name, "arguments": arguments})
                remaining = remaining.replace(text[idx:end_pos], "", 1)
                log(f"  Llama tool call: {name}({list(arguments.keys())})")
            _pos = end_pos
        except json.JSONDecodeError:
            _pos = idx + 1
    if tool_calls:
        return tool_calls, remaining.strip()

    # Format 1: <tool_call>{"name": "x", "arguments": {...}}</tool_call>
    pattern1 = r'<tool_call>\s*(.*?)\s*</tool_call>'
    for match in re.finditer(pattern1, text, re.DOTALL):
        content = match.group(1).strip()
        remaining = remaining.replace(match.group(0), "", 1)
        if not content:
            continue
        try:
            call_data = json.loads(content)
            tool_calls.append({
                "name": call_data.get("name", ""),
                "arguments": call_data.get("arguments", {}),
            })
        except json.JSONDecodeError:
            # The model often puts Format 2 (<function=X><parameter=Y>...</parameter></function>)
            # inside <tool_call> tags. Handle that first.
            func_in_tag = re.search(r'<function=([\w.-]+)>(.*)', content, re.DOTALL)
            if func_in_tag:
                fname = func_in_tag.group(1)
                params_text = func_in_tag.group(2)
                arguments = {}
                for pmatch in re.finditer(r'<parameter=(\w+)>\s*(.*?)\s*(?:</parameter>|$)', params_text, re.DOTALL):
                    arguments[pmatch.group(1)] = pmatch.group(2).strip()
                if arguments:
                    tool_calls.append({"name": fname, "arguments": arguments})
                    log(f"  Recovered function-in-tag: {fname}")
                    note_recovery(fname)
                else:
                    log(f"  Warning: function-in-tag but no params: {content[:100]}")
            else:
                # Try general garbled recovery
                recovered = recover_garbled_tool_json(content, text)
                if recovered:
                    tool_calls.append(recovered)
                else:
                    log(f"  Warning: unrecoverable tool_call JSON: {content[:100]}")

    # Format 2: <function=name><parameter=key>value</parameter>...</function>
    if not tool_calls:
        pattern2 = r'<function=([\w.-]+)>(.*?)</function>'
        for match in re.finditer(pattern2, text, re.DOTALL):
            func_name = match.group(1)
            params_text = match.group(2)
            arguments = {}
            for pmatch in re.finditer(r'<parameter=(\w+)>\s*(.*?)\s*</parameter>', params_text, re.DOTALL):
                arguments[pmatch.group(1)] = pmatch.group(2)
            tool_calls.append({"name": func_name, "arguments": arguments})
            remaining = remaining.replace(match.group(0), "", 1)

    # Format 3: <|tool_call|>...<|/tool_call|> (some model versions)
    if not tool_calls:
        pattern3 = r'<\|tool_call\|>\s*(.*?)\s*<\|/tool_call\|>'
        for match in re.finditer(pattern3, text, re.DOTALL):
            remaining = remaining.replace(match.group(0), "", 1)
            try:
                call_data = json.loads(match.group(1))
                tool_calls.append({
                    "name": call_data.get("name", ""),
                    "arguments": call_data.get("arguments", {}),
                })
            except json.JSONDecodeError:
                recovered = recover_garbled_tool_json(match.group(1))
                if recovered:
                    tool_calls.append(recovered)

    # Format 4: Garbled — no tags at all, but parameter= patterns in raw text
    if not tool_calls:
        # Look for any tool name followed by parameter patterns
        tool_names_pattern = r'(?:mcp__[\w.-]+|Bash|Read|Write|Edit|Glob|Grep)'
        name_match = re.search(rf'"?name"?\s*[:=]\s*"?({tool_names_pattern})"?', text)
        param_matches = list(re.finditer(r'<parameter=(\w+)>\s*(.*?)\s*</parameter>', text, re.DOTALL))

        if name_match and param_matches:
            arguments = {}
            for pm in param_matches:
                arguments[pm.group(1)] = pm.group(2)
            tool_calls.append({"name": name_match.group(1), "arguments": arguments})
            remaining = text[:name_match.start()].strip()
            log(f"  Recovered tagless tool call: {name_match.group(1)}")
            note_recovery(name_match.group(1))
        elif param_matches:
            # We have parameters but no name — try to infer from param keys
            arguments = {}
            for pm in param_matches:
                arguments[pm.group(1)] = pm.group(2)
            if "command" in arguments:
                tool_calls.append({"name": "Bash", "arguments": arguments})
                log(f"  Inferred Bash tool call from 'command' parameter")
                note_recovery("Bash")
            elif "file_path" in arguments:
                tool_calls.append({"name": "Read", "arguments": arguments})
                log(f"  Inferred Read tool call from 'file_path' parameter")
                note_recovery("Read")
            elif "pattern" in arguments:
                tool_calls.append({"name": "Glob", "arguments": arguments})
                log(f"  Inferred Glob tool call from 'pattern' parameter")
                note_recovery("Glob")
            if tool_calls:
                remaining = text[:param_matches[0].start()].strip()

    # Deduplicate tool calls (model sometimes emits same call in multiple formats)
    seen = set()
    deduped = []
    for tc in tool_calls:
        key = tc["name"]
        if key not in seen:
            seen.add(key)
            deduped.append(tc)
        else:
            log(f"  Deduped: {key}")
    tool_calls = deduped

    # Clean remaining text: strip any leftover <function=...> or <tool_call> fragments
    remaining = re.sub(r'<function=[\w.-]+>.*?</function>', '', remaining, flags=re.DOTALL)
    remaining = re.sub(r'</?tool_call>', '', remaining)
    remaining = remaining.strip()

    return tool_calls, remaining
