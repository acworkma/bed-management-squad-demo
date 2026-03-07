# Architecture Decisions — Patient Flow / Bed Management Demo

**Author:** Maverick (Lead/Architect)
**Date:** 2026-03-07
**Status:** PROPOSED

---

## ADR-001: In-Memory State Store (No Database)

**Context:** The spec requires beds, patients, tasks, transports, and reservations state. This is a demo, not a production EHR.

**Decision:** Use Python in-memory data structures (dicts keyed by entity ID, thread-safe via asyncio locks). No database, no ORM, no migrations.

**Rationale:** Simplest thing that works. Demo resets state on every scenario run. No persistence needed between restarts. Eliminates an entire infrastructure dependency.

**Consequence:** State is lost on container restart. This is acceptable — scenarios are self-contained and re-runnable.

---

## ADR-002: Event Sourcing Lite — Events as System Truth

**Context:** Spec §8 mandates an append-only event timeline as "system truth."

**Decision:** Implement a lightweight event store as a Python list with monotonic sequence numbers. Events are Pydantic models, immutable once appended. State views (bed board, patient queue) can be rebuilt from events, but for performance we maintain materialized in-memory state alongside events.

**Rationale:** Full event sourcing (rebuild state from events) is overkill for a demo. Instead, dual-write: tools mutate state AND emit events atomically. The event timeline is the audit trail; the state dict is the fast read path.

**Consequence:** State and events could theoretically drift. Acceptable for demo scope. If needed, add a consistency check that replays events and compares.

---

## ADR-003: Tool-Backed State Mutation — Agents Never Mutate Directly

**Context:** Spec §6.2 rule: "Agents do not directly mutate state from free-form text. State changes occur only via tool-backed actions that emit events."

**Decision:** Agent tool functions are the single mutation boundary. Each tool function: (1) validates input, (2) checks state-machine transition legality, (3) mutates in-memory state, (4) emits the corresponding event, (5) returns a result to the agent. Agents receive tool definitions via Foundry function-calling. The orchestrator executes tool calls locally.

**Rationale:** This is the core architectural invariant. It makes the demo auditable, debuggable, and visually coherent (every state change has a corresponding event and was triggered by an agent action).

**Consequence:** Agent prompts must be carefully crafted to use tools rather than describing state changes in prose. The orchestrator must reject any agent response that doesn't use tools when state change is needed.

---

## ADR-004: Supervisor Orchestration Pattern

**Context:** Spec §6.1 defines a Flow Coordinator as supervisor with 4-5 specialist agents.

**Decision:** Use a supervisor pattern where the Flow Coordinator agent decides which specialist to invoke next. The orchestration loop: (1) Coordinator receives trigger, (2) Coordinator calls a "route to specialist" tool or outputs a structured routing decision, (3) Orchestrator invokes the specialist agent with context, (4) Specialist responds with tool calls, (5) Loop back to Coordinator for next step. All agent interactions go through Foundry SDK `agents` API.

**Rationale:** The supervisor pattern is the simplest multi-agent pattern. It avoids complex peer-to-peer agent communication. The Coordinator is the single decision point, making the flow predictable and demo-friendly.

**Consequence:** The Coordinator agent's system prompt must be comprehensive about the workflow. Specialists are stateless — they receive context per invocation and don't maintain conversation history across calls.

---

## ADR-005: Single Container, Two Processes (API + Static UI)

**Context:** Need to deploy both Python API and React UI. Options: (A) two ACA containers, (B) single container with both.

**Decision:** Single container. Build the React app to static files at Docker build time. FastAPI serves static files at `/` and API at `/api/*`. One ACA container app, one ingress, one URL.

**Rationale:** Simplest deployment topology. No CORS in production. One URL to share for demo. Fewer moving parts = fewer things to break during a live demo.

**Consequence:** During development, frontend and backend run as separate dev servers (Vite on :5173, FastAPI on :8000) with CORS enabled. Dockerfile has a multi-stage build: Node stage builds UI, Python stage copies static output and runs API.

---

## ADR-006: SSE for Real-Time UI Updates

**Context:** The UI needs to update in real-time as scenarios run (events appearing, agent messages flowing, state changing).

**Decision:** Use Server-Sent Events (SSE) from FastAPI. Endpoints: `GET /api/events/stream` and `GET /api/agent-messages/stream`. Frontend subscribes via `EventSource` API. Polling fallback available via standard GET endpoints.

**Rationale:** SSE is simpler than WebSockets for uni-directional server→client streaming. Native browser support, no libraries needed. Perfect for an append-only event feed.

**Consequence:** SSE connections must be managed carefully in ACA (timeouts, reconnection). Frontend needs reconnection logic with last-seen sequence number.

---

## ADR-007: Scenario Reset on Trigger

**Context:** Demo scenarios must be re-runnable and deterministic.

**Decision:** `POST /api/scenario/happy-path` and `POST /api/scenario/disruption-replan` each: (1) clear all state (beds, patients, tasks, transports, events, messages), (2) seed initial state (predetermined bed layout, incoming patient), (3) kick off the orchestration loop. The endpoint returns 202 Accepted immediately; the scenario runs asynchronously.

**Rationale:** Demo operator needs to run scenarios repeatedly. Clean slate each time ensures deterministic, impressive results. Async execution means the UI shows events streaming in real-time.

**Consequence:** Only one scenario can run at a time. Need a mutex or "scenario in progress" flag to prevent concurrent runs.

---

## ADR-008: Agent System Prompts Define Persona + Available Tools

**Context:** Each Foundry agent needs a system prompt and tool definitions.

**Decision:** Agent system prompts are stored as text files in `src/api/agents/prompts/` (one file per agent). Tool definitions are Python functions with type annotations, converted to Foundry tool schemas at agent creation time. The `build_agents.py` script reads prompts and tool schemas to create/update agents.

**Rationale:** Prompts as files are version-controlled, reviewable, and tweakable without code changes. Tool schemas derived from Python types ensure consistency between what agents think they can call and what actually exists.

**Consequence:** Prompt engineering is iterative. The team should expect to tune prompts during Phase 3 integration.

---

## ADR-009: Chat Transcript Model

**Context:** Spec §5.1 requires agent conversation with intent tags (PROPOSE, VALIDATE, EXECUTE, ESCALATE).

**Decision:** Agent messages are stored as a list of `AgentMessage` objects: `{id, timestamp, agentName, agentRole, content, intentTag, relatedEventIds[]}`. Intent tags are derived from agent output — either parsed from structured output or inferred by the orchestrator based on the action taken. Messages are append-only like events.

**Rationale:** Keeping messages separate from events maintains the two-layer model. Intent tags make the conversation scannable. Related event IDs create the cross-reference between chat and timeline.

**Consequence:** Intent tag assignment may need a simple classifier or structured output format from agents. Start with rule-based (tool call → EXECUTE, validation response → VALIDATE, etc.) and upgrade if needed.

---

## ADR-010: Predictive Capacity as Simulated Confidence Scores

**Context:** Spec §1 mentions "predictive bed assignment — rank candidate beds by probability of readiness within a time window."

**Decision:** The Predictive Capacity Agent returns simulated confidence scores, not real ML predictions. Scores are deterministic based on bed state and scenario script (e.g., a bed in CLEANING state that started 20 min ago gets 85% readiness confidence for 30-min window). The agent's LLM generates reasoning text explaining the ranking.

**Rationale:** This is a demo. Real ML predictions require training data we don't have. Simulated scores + LLM reasoning text achieves the same visual/narrative impact.

**Consequence:** Scores and ETAs are hardcoded per scenario. The prediction tool returns pre-configured values. The LLM adds the "why" narrative on top.

---

## Summary of Key Constraints

1. Agents act ONLY through tools — never free-text state mutation
2. In-memory state — no database
3. Single container deployment — API serves static UI
4. SSE for real-time updates
5. Supervisor orchestration — Flow Coordinator routes to specialists
6. Scenarios reset state completely on each run
7. Predictions are simulated, not ML-based
8. Foundry SDK (`azure-ai-projects>=2.0.0b1`) for all LLM/agent interactions
9. `DefaultAzureCredential` for auth — no API keys
10. Dark mode is default and only theme
