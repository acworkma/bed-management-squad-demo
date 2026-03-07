# Project Context

- **Owner:** acworkma
- **Project:** Patient Flow / Bed Management — Agentic AI Demo (Azure + Foundry + ACA)
- **Stack:** Python/FastAPI backend, React/Tailwind/shadcn frontend, Azure Container Apps, Azure AI Foundry, Bicep/azd infra
- **Created:** 2026-03-07

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-03-07 — Spec Decomposition & Architecture Decisions

**Architecture decisions made (10 ADRs):**
- ADR-001: In-memory state store, no database (demo scope)
- ADR-002: Event sourcing lite — dual-write state + events, not full replay
- ADR-003: Tool-backed state mutation — agents never mutate directly (core invariant)
- ADR-004: Supervisor orchestration — Flow Coordinator routes to specialists
- ADR-005: Single container deployment (FastAPI serves static React build)
- ADR-006: SSE for real-time UI updates (not WebSockets)
- ADR-007: Scenario reset on trigger — clean slate each run, async execution
- ADR-008: Agent prompts as files in `src/api/agents/prompts/`, tools from Python type annotations
- ADR-009: Chat transcript model with intent tags (PROPOSE/VALIDATE/EXECUTE/ESCALATE)
- ADR-010: Predictive capacity uses simulated confidence scores, not real ML

**Key file paths:**
- Decomposition: `.squad/decisions/inbox/maverick-spec-decomposition.md`
- Architecture decisions: `.squad/decisions/inbox/maverick-architecture-decisions.md`

**Work distribution:** 23 WIs across 4 phases. Goose carries heaviest load (9 WIs — domain model through scenarios). Viper has 6 WIs (UI shell through polish). Iceman has 3 WIs (infra + deploy + CI/CD). Jester has 4 WIs (test framework through smoke tests). Maverick owns WI-001 (scaffolding) + ongoing code review.

**Key insight:** The critical path runs through WI-001 (scaffold) → WI-002/003 (domain+events) → WI-007/008 (API+tools) → WI-014 (orchestration) → WI-015/016 (scenarios). Goose is on the critical path for most of the project. Frontend and infra are parallelizable off the critical path.
