# Spec Decomposition — Patient Flow / Bed Management Agentic AI Demo

**Author:** Maverick (Lead/Architect)
**Date:** 2026-03-07
**Status:** PROPOSED
**Requested by:** acworkma

---

## Phase 1 — Foundation (Start Immediately, No Dependencies)

> Goal: Establish repo structure, domain primitives, infra skeleton, UI shell, and test harness. Everything here can run **in parallel**.

### WI-001 · Repo Scaffolding & Project Structure
- **Assigned to:** Maverick
- **Priority:** P0
- **Dependencies:** none
- **Complexity:** S
- **Description:** Create the canonical repo layout per spec §15. Set up `azure.yaml`, `src/api/` (Python project with pyproject.toml, FastAPI skeleton), `src/ui/` (React + Vite + Tailwind + shadcn/ui scaffold), `scripts/`, `infra/`, `.github/workflows/`. Establish shared constants (state enums) importable by both API and tests. Acceptance: `pip install -e src/api` works; `npm run dev` in `src/ui` starts a blank page.

### WI-002 · Domain Model — Entities & State Machines
- **Assigned to:** Goose
- **Priority:** P0
- **Dependencies:** WI-001
- **Complexity:** M
- **Description:** Implement Python data models for Bed, Patient, Task, Transport, and Reservation. Define state enums (Bed: OCCUPIED/RESERVED/DIRTY/CLEANING/READY/BLOCKED; Patient: AWAITING_BED/BED_ASSIGNED/TRANSPORT_READY/IN_TRANSIT/ARRIVED/DISCHARGED; Task: CREATED/ACCEPTED/IN_PROGRESS/COMPLETED/ESCALATED/CANCELLED). Include state-transition validation (e.g., Bed can only go DIRTY→CLEANING, not DIRTY→OCCUPIED). Acceptance: models importable, invalid transitions raise errors.

### WI-003 · Event System — Append-Only Store & Event Types
- **Assigned to:** Goose
- **Priority:** P0
- **Dependencies:** WI-001
- **Complexity:** M
- **Description:** Build an in-memory append-only event store. Define all event types from spec §8 as typed dataclasses/Pydantic models (PatientBedRequestCreated, PredictionGenerated, BedReserved, EVSTaskCreated, etc.). Each event has id, timestamp, type, entityId, payload, and optional stateDiff. Provide `publish_event()` that appends and notifies subscribers. Acceptance: events are immutable once published, full list retrievable, each event has a monotonic sequence number.

### WI-004 · Azure Infra — Bicep Modules & azd Config
- **Assigned to:** Iceman
- **Priority:** P0
- **Dependencies:** WI-001
- **Complexity:** L
- **Description:** Author Bicep modules: `infra/main.bicep` (orchestrator), `infra/modules/foundry.bicep` (Foundry resource + project), `infra/modules/aca.bicep` (ACA environment + container app + ACR), `infra/modules/observability.bicep` (Log Analytics + App Insights). Configure `azure.yaml` for azd with post-provision hook pointing to `scripts/build_agents.py`. Define `infra/parameters.bicepparam` with sensible defaults. Acceptance: `azd provision` creates all resources in a new resource group; container app gets env vars per spec §13.

### WI-005 · UI Shell — Dark Mode Three-Pane Layout
- **Assigned to:** Viper
- **Priority:** P0
- **Dependencies:** WI-001
- **Complexity:** M
- **Description:** Initialize React app with Vite, Tailwind CSS (dark mode default), and shadcn/ui. Build the three-pane layout shell: Ops Dashboard (left), Agent Conversation (right-top), Event Timeline (right-bottom). Use CSS Grid or Flexbox with resizable panes. Dark theme tokens throughout. Acceptance: running `npm run dev` shows the three-pane layout with placeholder content, fully dark-mode, responsive to window resize.

### WI-006 · Test Framework Setup
- **Assigned to:** Jester
- **Priority:** P0
- **Dependencies:** WI-001
- **Complexity:** S
- **Description:** Configure pytest for `src/api/` (with async support via pytest-asyncio, httpx for API testing). Configure Vitest for `src/ui/` with React Testing Library. Add npm scripts and pyproject.toml test commands. Acceptance: `pytest` and `npm test` both run and pass with a trivial placeholder test each.

**Parallelism:** WI-002, WI-003, WI-004, WI-005, WI-006 can all start once WI-001 is done. WI-001 is a brief scaffolding task (hours, not days) so Phase 1 effectively starts in parallel.

---

## Phase 2 — Core Implementation (Depends on Phase 1)

> Goal: Build the API surface, agent tools, Foundry integration, and all three UI panes with real component structure.

### WI-007 · API Endpoints & FastAPI App
- **Assigned to:** Goose
- **Priority:** P0
- **Dependencies:** WI-002, WI-003
- **Complexity:** M
- **Description:** Implement the FastAPI application with all spec §10 endpoints: `GET /api/state` (returns full state snapshot), `GET /api/events` (event feed with optional `?since=` sequence filter), `GET /api/agent-messages` (chat transcript), `POST /api/scenario/happy-path`, `POST /api/scenario/disruption-replan`. Add CORS middleware for UI dev. Include SSE endpoint `GET /api/events/stream` for real-time push. Acceptance: all endpoints return valid JSON, scenario endpoints return 202 Accepted immediately and run async.

### WI-008 · Agent Tool Definitions
- **Assigned to:** Goose
- **Priority:** P0
- **Dependencies:** WI-002, WI-003
- **Complexity:** M
- **Description:** Implement all spec §9 tool functions as Python callables: `get_patient()`, `get_beds()`, `get_tasks()`, `reserve_bed()`, `release_bed_reservation()`, `create_task()`, `update_task()`, `schedule_transport()`, `publish_event()`, `escalate()`. Each tool validates input, mutates in-memory state via the domain model, and emits the corresponding event. Tools are the ONLY way agents change state. Acceptance: each tool can be called standalone in a test, produces correct state change and event.

### WI-009 · Build Agents Script (Foundry SDK)
- **Assigned to:** Goose
- **Priority:** P1
- **Dependencies:** WI-004
- **Complexity:** M
- **Description:** Write `scripts/build_agents.py` per spec §14. Authenticate via `DefaultAzureCredential`. Use `AIProjectClient` to create/update 5-6 agents (flow-coordinator, predictive-capacity, bed-allocation, evs-tasking, transport-ops, optionally policy-safety). Each agent gets a system prompt defining its role and available tools. Script is idempotent — updates existing agents, creates missing ones. Outputs JSON map of agent name→ID. Acceptance: script runs without error against a live Foundry project, outputs valid JSON.

### WI-010 · Ops Dashboard Components
- **Assigned to:** Viper
- **Priority:** P1
- **Dependencies:** WI-005
- **Complexity:** M
- **Description:** Build the left-pane Ops Dashboard with three sub-views: (1) Patient Queue — card list showing patient name, status badge, current location, time waiting; (2) Bed Board — grid/table of beds with color-coded status chips (OCCUPIED=red, READY=green, CLEANING=yellow, etc.); (3) Transport Queue — list of scheduled/active transports with status. All components use shadcn/ui primitives. Acceptance: components render with mock data, status badges are color-coded, layout is clean and scannable.

### WI-011 · Agent Conversation Pane
- **Assigned to:** Viper
- **Priority:** P1
- **Dependencies:** WI-005
- **Complexity:** M
- **Description:** Build the right-top Agent Conversation pane. Show a chat-style transcript with: agent name/avatar, message text, intent tag badge (PROPOSE/VALIDATE/EXECUTE/ESCALATE with distinct colors), timestamp, and clickable links to related events in the timeline. Auto-scroll to latest message. Acceptance: renders mock conversation data, intent tags are visually distinct, clicking event link scrolls timeline pane.

### WI-012 · Event Timeline Pane
- **Assigned to:** Viper
- **Priority:** P1
- **Dependencies:** WI-005
- **Complexity:** M
- **Description:** Build the right-bottom Event Timeline pane. Render an append-only vertical timeline of events. Each entry shows: event type (color-coded icon), timestamp, entity reference, summary line. Clicking expands to show full payload JSON and state diff (before/after). New events animate in from bottom. Acceptance: renders mock event data, expand/collapse works, state diffs are syntax-highlighted.

### WI-013 · ACA Deployment Configuration
- **Assigned to:** Iceman
- **Priority:** P1
- **Dependencies:** WI-004, WI-007
- **Complexity:** M
- **Description:** Create Dockerfile(s) for the application (single container serving both API and static UI build, or two containers — decide based on simplicity). Configure ACA ingress, scaling rules, env var injection per spec §13 (PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME, AGENT_IDS_JSON, APP_THEME=dark). Wire ACR push into azd deploy flow. Acceptance: `azd deploy` builds image, pushes to ACR, updates ACA container app, app is reachable via ACA URL.

**Parallelism:** WI-007 + WI-008 run in parallel (both depend on domain model + events). WI-009 runs in parallel (depends on infra). WI-010 + WI-011 + WI-012 run in parallel (all depend on UI shell). WI-013 starts once infra and API are ready.

---

## Phase 3 — Integration & Scenarios (Depends on Phase 2)

> Goal: Wire agents together, implement demo scenarios end-to-end, connect frontend to backend, write core tests.

### WI-014 · Multi-Agent Orchestration Loop
- **Assigned to:** Goose
- **Priority:** P1
- **Dependencies:** WI-007, WI-008, WI-009
- **Complexity:** L
- **Description:** Implement the orchestration engine that runs agent conversations. Flow Coordinator receives a trigger (e.g., new patient bed request), decides which specialist agents to invoke, manages turn-taking. Each agent call goes through Foundry SDK, receives tool-call responses, and the orchestrator executes tools locally. Agent messages are captured to the chat transcript with intent tags. The two-layer model (chat + events) is enforced here. Acceptance: triggering a patient bed request produces a multi-turn agent conversation with corresponding events in the timeline.

### WI-015 · Scenario A — Happy Path
- **Assigned to:** Goose
- **Priority:** P1
- **Dependencies:** WI-014
- **Complexity:** M
- **Description:** Implement `POST /api/scenario/happy-path` that seeds initial state (beds in various states, ED patient arriving) and triggers the orchestration loop. Expected flow per spec §11: patient requests bed → predictive ranking → validation → reserve → EVS clean → bed ready → transport scheduled → patient arrives. Each step produces correct events and state transitions. Acceptance: calling the endpoint produces a complete event timeline and agent conversation matching the happy path narrative.

### WI-016 · Scenario B — Disruption & Replan
- **Assigned to:** Goose
- **Priority:** P1
- **Dependencies:** WI-014
- **Complexity:** L
- **Description:** Implement `POST /api/scenario/disruption-replan` that starts like Scenario A but introduces an EVS delay mid-flow. Expected flow: SLA risk detected → escalation → fallback plan → reservation swap → transport reschedule → resolution despite disruption. This is the "agentic wow" moment — agents visibly reasoning about alternatives. Acceptance: calling the endpoint produces the disruption narrative with SlaRiskDetected, ReservationReleased, FallbackPlanSet events and visible agent re-planning in transcript.

### WI-017 · Frontend-Backend Integration
- **Assigned to:** Viper
- **Priority:** P1
- **Dependencies:** WI-007, WI-010, WI-011, WI-012
- **Complexity:** M
- **Description:** Replace mock data with live API calls. Implement React hooks/services for: fetching state (`GET /api/state`), subscribing to events (SSE or polling `GET /api/events`), fetching agent messages, and triggering scenarios. Wire scenario trigger buttons into the Ops Dashboard header. State updates flow reactively to all three panes. Acceptance: clicking "Run Happy Path" triggers the scenario and all three panes update in real-time as events and agent messages stream in.

### WI-018 · Domain Model & API Tests
- **Assigned to:** Jester
- **Priority:** P1
- **Dependencies:** WI-002, WI-003, WI-007, WI-008
- **Complexity:** M
- **Description:** Write unit tests for: (1) state machine transitions — valid and invalid for Bed/Patient/Task; (2) event emission — correct event types and payloads for each tool; (3) API endpoint responses — correct shapes, status codes, error handling. Target >80% coverage of domain model and tools. Acceptance: `pytest` passes with all tests green, covers happy paths and error cases for state transitions.

**Parallelism:** WI-014 is the critical path. WI-015 + WI-016 are sequential (B extends A). WI-017 can start once API and UI components exist. WI-018 can run in parallel with all of Phase 3.

---

## Phase 4 — Polish & Deploy (Depends on Phase 3)

> Goal: Production-readiness for demo day. CI/CD, e2e tests, UI polish, optional 6th agent.

### WI-019 · CI/CD Pipeline
- **Assigned to:** Iceman
- **Priority:** P2
- **Dependencies:** WI-013
- **Complexity:** M
- **Description:** Create `.github/workflows/deploy.yml` with: lint (ruff + eslint), test (pytest + vitest), build (Docker image), deploy (azd deploy or direct ACR push + ACA update). Use GitHub OIDC for Azure auth. Acceptance: push to main triggers full pipeline; green build deploys to ACA automatically.

### WI-020 · End-to-End Scenario Tests
- **Assigned to:** Jester
- **Priority:** P2
- **Dependencies:** WI-015, WI-016
- **Complexity:** M
- **Description:** Write integration tests that call the scenario endpoints and validate the full event sequence. Scenario A test: assert all expected events appear in order, final patient state is ARRIVED. Scenario B test: assert SlaRiskDetected and ReservationReleased events appear, final state resolves successfully. Acceptance: tests pass against a running local API instance.

### WI-021 · Smoke Test Script
- **Assigned to:** Jester
- **Priority:** P2
- **Dependencies:** WI-013
- **Complexity:** S
- **Description:** Write `scripts/smoke_test.sh` that hits the deployed ACA endpoint, runs both scenarios, and validates HTTP 200s and non-empty responses. Used as post-deploy verification. Acceptance: script exits 0 on healthy deployment, exits 1 with clear error message on failure.

### WI-022 · UI Polish & Animations
- **Assigned to:** Viper
- **Priority:** P2
- **Dependencies:** WI-017
- **Complexity:** M
- **Description:** Add visual polish: loading spinners during scenario runs, smooth animations for new events/messages appearing, status transition animations on bed board, subtle glow effects for active agents. Ensure responsive behavior. Add scenario control buttons with clear labeling. Acceptance: demo feels polished and professional, no jarring layout shifts, animations enhance understanding of flow.

### WI-023 · Policy & Safety Agent (Optional)
- **Assigned to:** Goose
- **Priority:** P2
- **Dependencies:** WI-014
- **Complexity:** M
- **Description:** Add the optional 6th agent — Policy & Safety — that validates assignments against rules (e.g., isolation patients can't share rooms, acuity matching). Integrates into the orchestration loop as a validation step. Adds credibility to the "agentic" narrative. Acceptance: agent participates in conversation with VALIDATE intent tags, blocks unsafe assignments with clear reasoning.

**Parallelism:** WI-019, WI-020, WI-021, WI-022, WI-023 can all run in parallel.

---

## Summary View

| Phase | WI Count | Critical Path | Parallelism |
|-------|----------|---------------|-------------|
| 1 — Foundation | 6 | WI-001 (scaffold) unlocks all others | 5 items in parallel after scaffold |
| 2 — Core | 7 | WI-007 + WI-008 (API + tools) | Backend (3) ∥ Frontend (3) ∥ Infra (1) |
| 3 — Integration | 5 | WI-014 → WI-015 → WI-016 (orchestration chain) | Tests ∥ Frontend integration |
| 4 — Polish | 5 | None critical | All 5 in parallel |

**Total: 23 work items** (10 P0, 9 P1, 4 P2)

### Assignment Distribution

| Member | Work Items | Focus |
|--------|-----------|-------|
| Maverick | WI-001 | Scaffolding + architecture oversight + code review |
| Goose | WI-002, WI-003, WI-007, WI-008, WI-009, WI-014, WI-015, WI-016, WI-023 | Domain model, API, tools, agents, scenarios |
| Viper | WI-005, WI-010, WI-011, WI-012, WI-017, WI-022 | UI shell, components, integration, polish |
| Iceman | WI-004, WI-013, WI-019 | Infra, deployment, CI/CD |
| Jester | WI-006, WI-018, WI-020, WI-021 | Test harness, unit/integration/e2e tests, smoke tests |
