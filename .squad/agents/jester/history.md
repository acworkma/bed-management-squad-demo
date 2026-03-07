# Project Context

- **Owner:** acworkma
- **Project:** Patient Flow / Bed Management — Agentic AI Demo (Azure + Foundry + ACA)
- **Stack:** Python/FastAPI backend, React/Tailwind/shadcn frontend, Azure Container Apps, Azure AI Foundry, Bicep/azd infra
- **Created:** 2026-03-07

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-03-07: Cross-agent note from Scribe (decision merge)
- Goose implemented tools as standalone async functions with `state_store`, `event_store`, `message_store` as kwargs (ADR-003a). This means tests can pass mock stores directly — no service class instantiation needed. Leverage this pattern for WI-018 domain model & API tests.
