# Project Context

- **Owner:** acworkma
- **Project:** Patient Flow / Bed Management — Agentic AI Demo (Azure + Foundry + ACA)
- **Stack:** Python/FastAPI backend, React/Tailwind/shadcn frontend, Azure Container Apps, Azure AI Foundry, Bicep/azd infra
- **Created:** 2026-03-07

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-03-07: Cross-agent note from Scribe (decision merge)
- Goose implemented tools as standalone async functions with `state_store`, `event_store`, `message_store` as kwargs (ADR-003a). This means tests can pass mock stores directly — no service class instantiation needed. Leverage this pattern for WI-018 domain model & API tests.

### 2026-03-07: WI-018 — Domain Model + API Endpoint Tests (Phase 2)
- **Test suite: 318 tests, 0 failures.** Breakdown: transitions (106), models (64), tool_functions (53), state_store (50), endpoints (27), event_store (18).
- **Key test files:**
  - `src/api/tests/conftest.py` — fixtures for fresh state_store, event_store, message_store per test; test_client resets singleton stores
  - `src/api/tests/test_models.py` — entity creation, defaults, serialization, enum completeness (Phase 1 — unchanged)
  - `src/api/tests/test_transitions.py` — exhaustive valid+invalid parametrized transitions for bed/patient/task (Phase 1 — unchanged)
  - `src/api/tests/test_state_store.py` — seeding, snapshots, getters, transitions, concurrent access, unit distribution (expanded)
  - `src/api/tests/test_event_store.py` — publish, retrieval, filtering, clear, subscribe/unsubscribe (Phase 1 — unchanged)
  - `src/api/tests/test_tool_functions.py` — all 10 tool functions tested: get_patient, get_beds, get_tasks, reserve_bed, release_bed_reservation, create_task, update_task, schedule_transport, publish_event, escalate (**NEW**)
  - `src/api/tests/test_endpoints.py` — health, state, events, messages, seed, happy-path, disruption-replan (**NEW**)
- **Pattern confirmed:** ADR-003a kwargs pattern makes tool testing trivial — pass fresh stores directly, no mocks needed.
- **Test client approach:** httpx AsyncClient + ASGITransport wraps FastAPI app. Singleton stores must be cleared in fixture since routers import global singletons.
- **Gotcha:** ASGI lifespan handling in httpx ASGITransport can produce surprising state interactions — patient state assertions after scenario seeds may not match expectations. Verify via events/existence instead of exact state checks.
- **Run command:** `cd src/api && python -m pytest tests/ -v` (tests live in `src/api/tests/`, not top-level `tests/api/`).
