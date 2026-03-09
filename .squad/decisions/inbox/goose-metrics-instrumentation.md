# Decision: Per-Agent Metrics via Inline Instrumentation

- **Author:** Goose | **Date:** 2026-03-09 | **Status:** Implemented
- **Issue:** #1 (WI-024)

## Context
Need per-agent latency and token tracking for model evaluation without adding external dependencies or middleware.

## Decision
Instrument `_invoke_agent` directly inside `orchestrator.py` rather than introducing a decorator, middleware, or separate metrics module.

**Rationale:**
- `_invoke_agent` is a closure nested inside `_run_live` — it captures `state_store`, `event_store`, `message_store`, and `deployment` from the enclosing scope. A decorator would need all that context passed explicitly.
- Keeping metrics types (`AgentMetrics`, `ScenarioMetrics`) as TypedDicts in the same file avoids import cycles and keeps the instrumentation self-contained.
- Token counts are accumulated across multi-round tool-call loops using `response.usage` from the Responses API. Used `getattr(response, "usage", None)` for safe access.
- Simulated functions return zero-token metrics with real wall-clock latency, so downstream consumers get a consistent shape regardless of mode.

## Consequences
- `_invoke_agent` return type changed from `str` to `dict` (private nested function — no external callers affected).
- `run_scenario()` return dict now always includes `"metrics"` key on success paths and `"mode"` key on all paths.
- No new files, no new dependencies, no changes to public function signatures.
