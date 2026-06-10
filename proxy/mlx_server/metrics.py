"""In-memory metrics collector for the observability dashboard.

Thread-safe and memory-bounded (a fixed-size ring buffer of recent requests).
Pure module — no MLX dependency — so it imports anywhere and is unit-testable.

Recording must never break the request path: callers should treat every
function here as fire-and-forget. The functions themselves don't raise on
normal input; if you pass something odd, they degrade rather than throw.
"""

import threading
import time
from collections import deque, defaultdict

# How many recent requests to keep for the activity feed.
RECENT_MAXLEN = 50

_lock = threading.Lock()

_state = {
    "started_at": None,      # epoch seconds when the server marked ready
    "model": None,
    "total_requests": 0,     # successful generations + errors
    "total_errors": 0,
    "in_flight": 0,
    "last_error": None,
    "total_prompt_tokens": 0,
    "total_output_tokens": 0,
    "total_gen_seconds": 0.0,  # summed generation time → avg tok/s
    "cache_hits": 0,
    "cache_misses": 0,
    "tool_calls_total": 0,
    "retries_total": 0,
    "recoveries_total": 0,
}
_tool_calls_by_name = defaultdict(int)
_recoveries_by_name = defaultdict(int)
_recent = deque(maxlen=RECENT_MAXLEN)


def mark_start(model):
    """Record the model name and server-ready time."""
    with _lock:
        _state["started_at"] = time.time()
        _state["model"] = model


def inc_inflight():
    with _lock:
        _state["in_flight"] += 1


def dec_inflight():
    with _lock:
        # Never go negative even if start/end get unbalanced.
        _state["in_flight"] = max(0, _state["in_flight"] - 1)


def note_recovery(tool_name):
    """A garbled tool call was recovered (from tool_calls.py)."""
    with _lock:
        _state["recoveries_total"] += 1
        _recoveries_by_name[tool_name or "?"] += 1


def record_request(detail):
    """Record a successful generation.

    `detail` keys (all optional): prompt_tokens, output_tokens, elapsed, tps,
    finish_reason, mode, tools (list[str]), retries (int), cache_hit (bool).
    """
    d = detail or {}
    prompt_tokens = int(d.get("prompt_tokens", 0) or 0)
    output_tokens = int(d.get("output_tokens", 0) or 0)
    elapsed = float(d.get("elapsed", 0.0) or 0.0)
    tps = float(d.get("tps", 0.0) or 0.0)
    tools = list(d.get("tools", []) or [])
    retries = int(d.get("retries", 0) or 0)
    cache_hit = bool(d.get("cache_hit", False))

    with _lock:
        _state["total_requests"] += 1
        _state["total_prompt_tokens"] += prompt_tokens
        _state["total_output_tokens"] += output_tokens
        _state["total_gen_seconds"] += elapsed
        _state["tool_calls_total"] += len(tools)
        _state["retries_total"] += retries
        if cache_hit:
            _state["cache_hits"] += 1
        else:
            _state["cache_misses"] += 1
        for name in tools:
            _tool_calls_by_name[name] += 1
        _recent.append({
            "ts": time.time(),
            "ok": True,
            "mode": d.get("mode", "plain"),
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "tps": round(tps, 1),
            "elapsed": round(elapsed, 2),
            "finish_reason": d.get("finish_reason", ""),
            "tools": tools,
            "retries": retries,
            "cache_hit": cache_hit,
        })


def record_error(message):
    """Record a failed request."""
    with _lock:
        _state["total_requests"] += 1
        _state["total_errors"] += 1
        _state["last_error"] = str(message)[:300]
        _recent.append({
            "ts": time.time(),
            "ok": False,
            "error": str(message)[:300],
        })


def snapshot():
    """Return a JSON-serializable copy of all metrics (safe to call any time)."""
    with _lock:
        now = time.time()
        started = _state["started_at"]
        uptime = (now - started) if started else 0
        cache_total = _state["cache_hits"] + _state["cache_misses"]
        cache_rate = (_state["cache_hits"] / cache_total) if cache_total else 0.0
        avg_tps = (
            _state["total_output_tokens"] / _state["total_gen_seconds"]
            if _state["total_gen_seconds"] > 0 else 0.0
        )
        return {
            "now": now,
            "started_at": started,
            "uptime_seconds": round(uptime, 1),
            "model": _state["model"],
            "total_requests": _state["total_requests"],
            "total_errors": _state["total_errors"],
            "in_flight": _state["in_flight"],
            "last_error": _state["last_error"],
            "total_prompt_tokens": _state["total_prompt_tokens"],
            "total_output_tokens": _state["total_output_tokens"],
            "avg_tps": round(avg_tps, 1),
            "cache_hits": _state["cache_hits"],
            "cache_misses": _state["cache_misses"],
            "cache_hit_rate": round(cache_rate, 3),
            "tool_calls_total": _state["tool_calls_total"],
            "tool_calls_by_name": dict(_tool_calls_by_name),
            "retries_total": _state["retries_total"],
            "recoveries_total": _state["recoveries_total"],
            "recoveries_by_name": dict(_recoveries_by_name),
            "recent": list(_recent),
        }


def reset():
    """Reset all metrics (used by tests)."""
    with _lock:
        for k, v in {
            "started_at": None, "model": None, "total_requests": 0,
            "total_errors": 0, "in_flight": 0, "last_error": None,
            "total_prompt_tokens": 0, "total_output_tokens": 0,
            "total_gen_seconds": 0.0, "cache_hits": 0, "cache_misses": 0,
            "tool_calls_total": 0, "retries_total": 0, "recoveries_total": 0,
        }.items():
            _state[k] = v
        _tool_calls_by_name.clear()
        _recoveries_by_name.clear()
        _recent.clear()
