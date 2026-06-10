"""Session-mode optimizations: browser and code.

Claude Code's harness sends a huge system prompt + 30+ tools. Open models get
lost in that context, so we auto-detect the session type and swap in a slim,
model-friendly prompt with a filtered tool list. Browser mode takes priority
over code mode (decided in generation.py).

Pure functions — no MLX dependency.
"""

from .config import log


# ─── Browser Mode Optimization ───────────────────────────────────────────────

BROWSER_SYSTEM_PROMPT = """You are a fast browser agent. You control a web browser via tools.

CORE RULES:
- ONLY use take_snapshot to see the page. NEVER use take_screenshot.
- take_snapshot returns a text DOM tree with uid attributes. Use these uids to click/fill.
- Chain actions quickly. Don't explain, just act.
- Navigate directly to URLs. Don't go to homepages first.

COMMENTING ON ARTICLES (Yahoo, news sites, etc.):
Comment boxes on most news sites are inside iframes that take_snapshot CANNOT see.
You MUST use evaluate_script to interact with comment boxes. Here is the exact process:

Step 1: Click the "Comments" button using its uid from the snapshot to open comments.
Step 2: Use evaluate_script to find and click the comment input inside the iframe:
  function: "() => { const frames = document.querySelectorAll('iframe'); for (const f of frames) { try { const doc = f.contentDocument || f.contentWindow.document; const el = doc.querySelector('[contenteditable=true], textarea, [role=textbox], .ow-comment-textarea, [data-spot-im-class=spcv_editor]'); if (el) { el.click(); el.focus(); return 'Found comment input in iframe'; } } catch(e) {} } return 'No comment input found'; }"

Step 3: Use evaluate_script to type your comment text into the focused element:
  function: "() => { const frames = document.querySelectorAll('iframe'); for (const f of frames) { try { const doc = f.contentDocument || f.contentWindow.document; const el = doc.querySelector('[contenteditable=true], textarea, [role=textbox], .ow-comment-textarea, [data-spot-im-class=spcv_editor]'); if (el) { el.focus(); el.innerText = 'YOUR COMMENT TEXT HERE'; el.dispatchEvent(new Event('input', {bubbles: true})); return 'Comment typed'; } } catch(e) {} } return 'Failed to type'; }"

Step 4: Do NOT click any Send/Post button. Leave the comment as a draft for the user to review.

IMPORTANT: Replace 'YOUR COMMENT TEXT HERE' with an actual thoughtful comment about the article.
The comment should be 2-3 sentences, relevant to the article content you read in the snapshot."""

# Only these tools are needed for browser control
BROWSER_TOOLS_ALLOW = {
    "mcp__chrome-devtools__navigate_page",
    "mcp__chrome-devtools__take_snapshot",
    "mcp__chrome-devtools__click",
    "mcp__chrome-devtools__fill",
    "mcp__chrome-devtools__type_text",
    "mcp__chrome-devtools__press_key",
    "mcp__chrome-devtools__evaluate_script",
    "mcp__chrome-devtools__select_page",
    "mcp__chrome-devtools__list_pages",
}

def looks_like_claude_code_browser_session(body):
    """A real Claude Code MCP browser session registers chrome-devtools tools.
    Direct clients (like ~/.local/browser-agent) bring their own system prompt
    and zero tools — we must NOT clobber those, or the model will call tools
    that don't exist on the client side."""
    tools = body.get("tools", [])
    return any(t.get("name", "") in BROWSER_TOOLS_ALLOW for t in tools)


def optimize_for_browser(body):
    """Strip Claude Code bloat: replace system prompt, keep only essential MCP tools.

    Only fires for actual Claude Code MCP browser sessions. Direct clients that
    bring their own system prompt + tool contract are passed through untouched.
    """
    if not looks_like_claude_code_browser_session(body):
        log("  Browser mode: passthrough (direct client, not Claude Code MCP)")
        return body

    # Replace massive system prompt with compact browser prompt
    body["system"] = BROWSER_SYSTEM_PROMPT

    # Filter tools to only essential chrome-devtools tools (no screenshot!)
    tools = body.get("tools", [])
    browser_tools = [t for t in tools if t.get("name", "") in BROWSER_TOOLS_ALLOW]
    if browser_tools:
        body["tools"] = browser_tools
        log(f"  Browser mode: {len(tools)} tools → {len(browser_tools)}")

    return body


# ─── Code Mode Optimization ──────────────────────────────────────────────────
#
# Claude Code's harness sends a ~10K-token system prompt and 30+ tools, all
# tuned for Claude. Open models (Llama, Qwen, etc.) get confused inside that
# wall of context and emit stock refusals like "I am not able to execute this
# task as it exceeds the limitations of the functions I have been given."
#
# This mode auto-detects Claude Code coding sessions (any of Bash/Read/Edit/
# Write/Grep/Glob in the tool list) and replaces the harness with a slim
# Llama-friendly prompt + filtered tool list. Browser mode takes priority.

CODE_SYSTEM_PROMPT = """You are a local coding assistant running on the user's Mac via MLX. You help with software engineering tasks: reading code, editing files, running shell commands, and searching codebases.

You have these tools available:
- Bash: run a shell command
- Read: read a file from disk (use absolute paths)
- Edit: replace exact text in an existing file
- Write: create a new file
- Grep: search file contents (ripgrep)
- Glob: find files by name pattern

RULES:
- Be concise. Skip preamble. Do the work, then give a brief result.
- Greetings, small talk, or questions about yourself: respond in plain text with NO tool calls.
- For real tasks: read files before editing them, use absolute paths, batch independent tool calls in parallel.
- NEVER say "I am not able to execute this task" or "this exceeds my limitations" — you have full tool access on this machine. If a request is genuinely unclear, ask one short clarifying question instead of refusing.
- When you call a tool, use the <tool_call> JSON format exactly as instructed. Do not wrap it in markdown."""

# Built-in Claude Code tools that signal a coding session and are worth keeping.
CODE_TOOLS_ALLOW = {
    "Bash",
    "Read",
    "Edit",
    "Write",
    "Grep",
    "Glob",
}

def looks_like_code_session(body):
    """Heuristic: if any of Claude Code's core file/shell tools are present,
    treat this as a coding session and apply the slim prompt."""
    tools = body.get("tools", [])
    tool_names = {t.get("name", "") for t in tools}
    return bool(tool_names & CODE_TOOLS_ALLOW)


def optimize_for_code(body):
    """Strip Claude Code bloat: replace the 10K-token harness prompt with a
    Llama-tuned coding prompt and filter tools down to the core 6."""
    body["system"] = CODE_SYSTEM_PROMPT

    tools = body.get("tools", [])
    code_tools = [t for t in tools if t.get("name", "") in CODE_TOOLS_ALLOW]
    if code_tools:
        stripped = len(tools) - len(code_tools)
        body["tools"] = code_tools
        log(f"  Code mode: {len(tools)} tools → {len(code_tools)} (stripped {stripped})")

    return body
