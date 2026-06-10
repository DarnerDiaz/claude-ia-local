"""Strip thinking blocks, stop tokens and reasoning artifacts from model output.

Pure functions — no MLX dependency. Tool-call tags (<tool_call>, <function=...>)
are deliberately preserved here; they are parsed downstream in tool_calls.py.
"""

import re


def strip_think_tags(text):
    """Remove thinking blocks from model reasoning output."""
    # Standard <think>...</think>
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    cleaned = re.sub(r'</think>', '', cleaned).strip()
    # Gemma 4 thinking: <|channel>thought\n...<channel|>
    cleaned = re.sub(r'<\|channel>thought\n.*?<channel\|>', '', cleaned, flags=re.DOTALL).strip()
    # Empty tool_call blocks
    cleaned = re.sub(r'<tool_call>\s*</tool_call>', '', cleaned).strip()
    return cleaned if cleaned else text


def clean_response(text):
    """Strip think tags, stop tokens, and reasoning artifacts (but preserve tool_call tags)."""
    text = strip_think_tags(text)
    # Llama 3.x: strip function-call prefix token
    text = text.replace('<|python_tag|>', '').strip()
    # Gemma 4: truncate at end-of-turn or start of a new turn
    for stop_marker in ['<turn|>', '<|turn>']:
        if stop_marker in text:
            text = text[:text.index(stop_marker)].strip()
            break

    # Remove reasoning preamble if present
    if text.lstrip().startswith("Thinking"):
        lines = text.split('\n')
        for i, line in enumerate(lines):
            s = line.strip()
            if any(s.startswith(p) for p in ['```', 'def ', 'class ', 'function ', 'import ', '#', '//', '<tool_call>']):
                return '\n'.join(lines[i:])

    return text
