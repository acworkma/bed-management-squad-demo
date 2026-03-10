# Decision: Runtime Config Store as Transparent Overlay

- **Author:** Goose | **Date:** 2026-03-10 | **Context:** Runtime model config endpoint

## Decision

Runtime model configuration (`model_deployment`, `agent_model_overrides`, `max_output_tokens`, `agent_max_tokens_overrides`) is managed via a `RuntimeConfigStore` singleton that overlays env var defaults. The orchestrator reads `runtime_config.get_config()` which merges runtime overrides with `settings.*` fallbacks.

## Rationale

- Eval script (`model_eval.py`) needs to swap models between runs without redeploying the container.
- The store follows the existing singleton + asyncio.Lock pattern (EventStore, MetricsStore, StateStore).
- `GET /api/config` returns the effective merged config; `PUT /api/config` applies partial overrides; `POST /api/config/reset` reverts to env vars.
- The orchestrator doesn't need to know whether a value came from env vars or a runtime PUT — the config store abstracts that.

## Impact

- `src/api/app/config_store.py` — new file
- `src/api/app/routers/config.py` — new router
- `src/api/app/agents/orchestrator.py` — reads from runtime config instead of parsing env vars directly
- `src/api/app/main.py` — registers config router
