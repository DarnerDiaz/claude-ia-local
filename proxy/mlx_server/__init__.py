"""MLX Native Anthropic Server — modular package.

The single-file `server.py` was split into focused modules so the core logic
(tool-call parsing, message conversion, mode detection) can be unit-tested
without loading MLX or a model. `server.py` remains the entry point and wires
these modules together.

Layout:
    config.py        — env configuration + log()
    text_cleaning.py — strip think tags / clean model output      (pure)
    tool_calls.py    — Anthropic<->model tool format + recovery     (pure)
    messages.py      — Anthropic message conversion + tokenization  (pure)
    modes.py         — browser / code session detection + prompts   (pure)
    metrics.py       — in-memory metrics collector for the dashboard (pure)
    dashboard.py     — self-contained observability HTML page        (pure)
    model_loader.py  — MLX model loading + chat template            (needs MLX)
    generation.py    — inference pipeline + prompt cache + retries   (needs MLX)
    http_app.py      — Anthropic Messages API + /dashboard + /metrics
"""
