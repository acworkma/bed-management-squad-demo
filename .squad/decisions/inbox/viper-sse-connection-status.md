# UI-002: useSSE Returns Connection Status Object

- **Author:** Viper
- **Date:** 2026-03-07
- **Status:** Implemented
- **Scope:** `src/ui/src/hooks/useSSE.ts`

## Decision

Changed `useSSE<T>` return type from `T[]` to `{ items: T[], connected: boolean }`.

## Rationale

The demo needs a live connection indicator in the toolbar. Rather than a separate hook or polling mechanism, the SSE hook already knows its own connection state via `onopen`/`onerror` — exposing it is the minimal change. All existing consumers updated to destructure.

## Impact

Any future component using `useSSE` gets connection status for free. The `SSEResult<T>` interface is exported for typing.
