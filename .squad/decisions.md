# Squad Decisions

## Active Decisions

### ADR-001: In-Memory State Store (No Database)
- **Author:** Maverick | **Date:** 2026-03-07 | **Status:** PROPOSED
- Use Python in-memory dicts (asyncio locks). No database. State resets on container restart. Acceptable for demo scope.

### ADR-002: Event Sourcing Lite — Dual-Write State + Events
- **Author:** Maverick | **Date:** 2026-03-07 | **Status:** PROPOSED
- Append-only event store with monotonic sequence numbers. State is materialized in-memory alongside events. Not full replay-based event sourcing.

### ADR-003: Tool-Backed State Mutation — Agents Never Mutate Directly
- **Author:** Maverick | **Date:** 2026-03-07 | **Status:** PROPOSED
- Agent tool functions are the single mutation boundary. Each tool validates, transitions state, emits event. Core architectural invariant.

### ADR-003a: Tools as Pure Functions with Store Arguments
- **Author:** Goose | **Date:** 2026-03-07 | **Status:** Implemented
- Standalone async functions in `tool_functions.py` receive `state_store`, `event_store`, `message_store` as kwargs. Stateless, testable, maps to Foundry function-calling pattern. Orchestrator injects singleton stores at dispatch time.

### ADR-004: Supervisor Orchestration Pattern
- **Author:** Maverick | **Date:** 2026-03-07 | **Status:** PROPOSED
- Flow Coordinator as supervisor routes to specialists. Single decision point, no peer-to-peer agent communication. Specialists are stateless per invocation.

### ADR-005: Single Container, Two Processes (API + Static UI)
- **Author:** Maverick | **Date:** 2026-03-07 | **Status:** PROPOSED
- React built to static files, served by FastAPI at `/`. API at `/api/*`. One ACA container, one ingress, one URL.

### ADR-006: SSE for Real-Time UI Updates
- **Author:** Maverick | **Date:** 2026-03-07 | **Status:** PROPOSED
- Server-Sent Events from FastAPI. Native browser EventSource. Simpler than WebSockets for uni-directional streaming.

### ADR-007: Scenario Reset on Trigger
- **Author:** Maverick | **Date:** 2026-03-07 | **Status:** PROPOSED
- Each scenario endpoint clears all state, seeds initial data, runs orchestration async. 202 Accepted. Mutex for concurrent run prevention.

### ADR-008: Agent System Prompts as Files + Tool Schemas from Python Types
- **Author:** Maverick | **Date:** 2026-03-07 | **Status:** PROPOSED
- Prompts in `src/api/app/agents/prompts/*.txt`. Tool definitions from Python annotations → Foundry schemas. `build_agents.py` creates/updates agents.

### ADR-009: Chat Transcript Model with Intent Tags
- **Author:** Maverick | **Date:** 2026-03-07 | **Status:** PROPOSED
- `AgentMessage` with intentTag (PROPOSE/VALIDATE/EXECUTE/ESCALATE). Rule-based tag assignment initially. Messages append-only, linked to events via relatedEventIds.

### ADR-010: Predictive Capacity as Simulated Confidence Scores
- **Author:** Maverick | **Date:** 2026-03-07 | **Status:** PROPOSED
- Deterministic scores based on bed state + scenario script. LLM generates reasoning narrative. Not real ML.

### INFRA-001: Keyless Auth & Security Posture
- **Author:** Iceman | **Date:** 2026-03-07 | **Status:** Implemented
- `disableLocalAuth: true` on AI Services — Entra ID only. ACR admin disabled — AcrPull via managed identity. OIDC federated credentials for CI/CD (no stored secrets). Container resources: 0.5 CPU, 1Gi, scale 0-1.

### UI-001: Frontend Data Architecture — Props-Down from ControlTower
- **Author:** Viper | **Date:** 2026-03-07 | **Status:** Implemented
- ControlTower is the single data owner (useApi + useSSE). Props down one level to leaf components. Color mapping centralized in `lib/colors.ts`. Components are pure renderers.

### PLAN-001: Spec Decomposition — 23 Work Items across 4 Phases
- **Author:** Maverick | **Date:** 2026-03-07 | **Status:** PROPOSED
- Phase 1 (Foundation): WI-001 through WI-006 — scaffold, domain model, events, infra, UI shell, tests
- Phase 2 (Core): WI-007 through WI-013 — API endpoints, tools, build_agents, 3 UI panes, ACA deploy config
- Phase 3 (Integration): WI-014 through WI-018 — orchestration loop, scenarios A+B, frontend-backend wiring, domain tests
- Phase 4 (Polish): WI-019 through WI-023 — CI/CD, e2e tests, smoke test, UI polish, optional policy agent
- Critical path: WI-001→WI-002/003→WI-007/008→WI-014→WI-015/016

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
