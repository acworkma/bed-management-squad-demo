# Project Context

- **Owner:** acworkma
- **Project:** Patient Flow / Bed Management — Agentic AI Demo (Azure + Foundry + ACA)
- **Stack:** Python/FastAPI backend, React/Tailwind/shadcn frontend, Azure Container Apps, Azure AI Foundry, Bicep/azd infra
- **Created:** 2026-03-07

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-03-07: WI-002 + WI-003 — Domain Model & Event System
- Implemented full domain model in `src/api/app/models/`: enums, entities (Pydantic v2), transitions (state machine validation), events
- Enums use `StrEnum` for JSON-friendly string serialization
- All six entities (Bed, Patient, Task, Transport, Reservation, AgentMessage) are Pydantic BaseModel with proper defaults and validators
- `InvalidTransitionError` carries entity_type, current, target for debuggable messages
- Bed transitions include Any→BLOCKED and BLOCKED→DIRTY per spec
- EventStore: append-only, monotonic sequence, asyncio.Lock, subscriber queues for SSE
- StateStore: in-memory dicts, asyncio.Lock on mutations, `validate_transition()` enforced on every state change
- Seed data: 12 beds across 4-North and 5-South units, 4 existing patients in ARRIVED state
- Snapshot method uses `model_dump(mode="json")` for datetime serialization
- Key file paths: `src/api/app/models/`, `src/api/app/events/event_store.py`, `src/api/app/state/store.py`

### 2026-03-07: WI-007 + WI-008 + WI-009 — API Endpoints, Tool Functions, Agent Build
- **MessageStore** (`src/api/app/messages/message_store.py`): mirrors EventStore pattern — publish, get_messages (index-based), subscribe/unsubscribe SSE queues. Singleton in `messages/__init__.py`.
- **Messages router** (`src/api/app/routers/messages.py`): wired to MessageStore with SSE streaming via subscriber queue, supports `?since=` index filter.
- **Scenarios router** (`src/api/app/routers/scenarios.py`): `POST /api/scenario/seed` resets+seeds state; happy-path creates an incoming patient + PatientBedRequestCreated event; disruption-replan blocks a READY bed to reduce capacity.
- **App lifespan** seeds initial state on startup.
- **Tool functions** (`src/api/app/tools/tool_functions.py`): 10 tools — `get_patient`, `get_beds`, `get_tasks`, `reserve_bed`, `release_bed_reservation`, `create_task`, `update_task`, `schedule_transport`, `publish_event`, `escalate`. Each validates inputs, mutates state via StateStore transitions, emits events, publishes agent messages.
- **Tool schemas** (`src/api/app/tools/tool_schemas.py`): OpenAI function-calling format schemas; per-agent tool sets mapping in `AGENT_TOOLS` dict for 6 agents.
- **Agent prompts** (`src/api/app/agents/prompts/*.txt`): 6 prompt files — flow-coordinator, predictive-capacity, bed-allocation, evs-tasking, transport-ops, policy-safety. Each includes role, responsibilities, decision framework, communication style, and available tools.
- **build_agents.py** (`scripts/build_agents.py`): supports both PROJECT_ENDPOINT (preferred) and PROJECT_CONNECTION_STRING (fallback); reads prompts from txt files; loads tool schemas from app module; idempotent create/update via list→match→create/update pattern; outputs JSON agent ID map.
- All 221 existing tests still pass; no regressions.

### 2026-03-09: WI-029 — Conciseness constraints added to agent prompts
- Appended `## Output Format` section to all 6 prompt files in `src/api/app/agents/prompts/`.
- Each section constrains response length and format: flow-coordinator (2-3 sentence updates, 100-word summaries), predictive-capacity (structured list, 2-sentence reasoning), bed-allocation (1-2 sentence results), evs-tasking (1-sentence confirmation), transport-ops (1-sentence confirmation), policy-safety (PASS/FAIL first line + 1-2 sentence reasoning).
- No existing content modified — append-only change to prompt files.
- All 9 existing tests pass; no regressions.

### 2026-03-09: WI-024 — Per-Agent Latency and Token Tracking
- Added `AgentMetrics` and `ScenarioMetrics` TypedDicts to `src/api/app/agents/orchestrator.py`
- Instrumented `_invoke_agent` (nested in `_run_live`) with `time.monotonic()` wall-clock timers, `response.usage` token extraction, and round counting across multi-round tool-call loops
- `_invoke_agent` now returns `{"text": str, "metrics": AgentMetrics}` instead of bare string; all callers in `_run_live` updated to destructure result
- `_run_live` collects per-agent metrics list, computes scenario totals (`total_latency_seconds`, `total_input_tokens`, `total_output_tokens`), and returns `ScenarioMetrics` under `"metrics"` key
- `_simulate_happy_path` and `_simulate_disruption_replan` return zero-token metrics with `time.monotonic()` latency tracking; `"mode": "simulated"` added to return dicts
- Structured logging added: `logger.info("agent=%s model=%s input_tokens=%d output_tokens=%d rounds=%d latency_s=%.2f", ...)`
- Used `getattr(response, "usage", None)` for safe access to response.usage (defensive against SDK variations)
- All 344 existing tests pass; no regressions
- Key file: `src/api/app/agents/orchestrator.py` (sole file changed)

### 2026-03-09: WI-025 — Expose metrics via /api/metrics endpoint
- Created `src/api/app/metrics/metrics_store.py`: in-memory store with asyncio.Lock, `record()`, `get_latest()`, `get_history(limit)`, `clear()` — mirrors EventStore/StateStore pattern
- Created `src/api/app/routers/metrics.py`: `GET /api/metrics` (latest run) and `GET /api/metrics/history?limit=N` (last N runs, most recent first); returns `{"message": "No scenario runs recorded yet"}` with 200 when empty
- Registered metrics router in `src/api/app/main.py` following existing pattern
- Updated `src/api/app/routers/scenarios.py`: both happy-path and disruption-replan background tasks now call `metrics_store.record(result["metrics"])` after orchestration completes
- Added `MetricsStore` fixture and singleton clearing in `src/api/tests/conftest.py`
- Created `src/api/tests/test_metrics.py`: 11 tests covering store unit tests (empty state, record, history ordering, limit, clear) and endpoint tests (empty responses, data after recording, limit param)
- All 355 tests pass; no regressions

### 2026-03-09: WI-026 — Per-agent model configuration with AGENT_MODEL_OVERRIDES
- Added `AGENT_MODEL_OVERRIDES: str = "{}"` to `src/api/app/config.py` Settings class — JSON string env var, parsed at usage time
- Updated `_run_live` in `src/api/app/agents/orchestrator.py`: parses `AGENT_MODEL_OVERRIDES` once into `_model_overrides` dict; `_invoke_agent` resolves model per agent via `_model_overrides.get(agent_name) or default_deployment`; resolved model set in `AgentMetrics` correctly
- Updated `scripts/build_agents.py`: reads `AGENT_MODEL_OVERRIDES` env var, resolves per-agent model when building Foundry agent definitions via `model_overrides.get(agent_name) or model_deployment`
- Pattern: env var is a JSON string, defensive `json.loads` with try/except fallback to empty dict — consistent with existing `AGENT_MAX_TOKENS_OVERRIDES` pattern
- All 355 tests pass; no regressions

### 2026-03-09: WI-028 — Add max_output_tokens to Responses API calls
- Added `MAX_OUTPUT_TOKENS: int = 1024` and `AGENT_MAX_TOKENS_OVERRIDES: str = "{}"` to `src/api/app/config.py` Settings
- `AGENT_MAX_TOKENS_OVERRIDES` is a JSON string env var for per-agent overrides (e.g. `'{"flow-coordinator":2048}"`); parsed once in `_run_live` with a `json.loads` + fallback on decode error
- Resolved token limit per agent: `override_dict.get(agent_name) or settings.MAX_OUTPUT_TOKENS`
- Passed `max_output_tokens=resolved_value` to **both** `responses.create()` calls in `_invoke_agent` (initial and tool-result follow-ups)
- Added `max_output_tokens` field to `AgentMetrics` TypedDict and populated it in the metrics dict
- Truncation handling: check `response.status == "incomplete"` after each API call; log a warning and break out of tool-call loop on truncation (don't crash)
- All 355 tests pass; no regressions
- Key files changed: `src/api/app/config.py`, `src/api/app/agents/orchestrator.py`
