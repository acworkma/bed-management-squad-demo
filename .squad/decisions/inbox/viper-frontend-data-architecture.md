# Decision: Frontend Data Architecture — Props-Down from ControlTower

**Author:** Viper (Frontend)
**Date:** 2026-03-07
**Status:** Implemented
**Work Items:** WI-010, WI-011, WI-012

## Context

Phase 2 required wiring 5 placeholder components to live API data (polling + SSE). Needed to decide where data-fetching hooks live and how data flows.

## Decision

- **ControlTower** is the single data owner — it calls `useApi()` (polling) and `useSSE()` (streaming) and passes typed props down to all child components.
- No prop drilling beyond one level (ControlTower → leaf components). If this grows, we'd introduce context — but for 5 components, props are simpler and more explicit.
- SSE hooks are generic (`useSSE<T>(url)`) so they're reusable for any future stream endpoint.
- Color mapping is centralized in `lib/colors.ts` rather than scattered across components. All state→color logic lives in one file.

## Consequences

- Adding a new data source requires touching ControlTower (add hook + pass prop). Acceptable at this scale.
- Components are pure renderers — easy to test with mock data, no internal fetch logic.
