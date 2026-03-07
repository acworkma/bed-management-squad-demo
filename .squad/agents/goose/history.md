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
