# Decision: Tools as pure functions with store arguments

**Date:** 2026-03-07  
**Author:** Goose (Backend Developer)  
**Status:** Implemented  

## Context
WI-008 required implementing agent tool functions that are the sole path for state mutations (ADR-003). Two patterns were considered: (1) tools as class methods on a service object, or (2) tools as standalone async functions that receive stores as keyword arguments.

## Decision
Chose standalone async functions in `tool_functions.py`. Each tool takes `state_store`, `event_store`, and `message_store` as keyword arguments. This keeps tools stateless/testable without needing to instantiate a service class, and maps directly to the Foundry function-calling pattern where each tool invocation is independent.

## Consequences
- Tools are easily testable in isolation by passing mock stores.
- The orchestration layer (future WI) will need to inject the singleton stores when dispatching tool calls from agent responses.
- All state mutations flow through `StateStore.transition_*` methods, preserving the state-machine invariant.
