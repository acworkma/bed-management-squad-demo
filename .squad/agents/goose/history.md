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
