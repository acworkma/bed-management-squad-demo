# Project Context

- **Owner:** acworkma
- **Project:** Patient Flow / Bed Management — Agentic AI Demo (Azure + Foundry + ACA)
- **Stack:** Python/FastAPI backend, React/Tailwind/shadcn frontend, Azure Container Apps, Azure AI Foundry, Bicep/azd infra
- **Created:** 2026-03-07

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-03-07: WI-005 — UI Shell Created

- **UI lives in `src/ui/`** — fully self-contained Vite + React + Tailwind + TypeScript project
- **Three-pane layout** via CSS Grid: left 55% (Ops Dashboard with stacked Patient Queue / Bed Board / Transport Queue), right 45% split vertically into Agent Conversation (55%) and Event Timeline (45%)
- **Color tokens** defined in `tailwind.config.ts` under `tower-*` namespace: bg, surface, border, accent (teal #06b6d4), warning (amber), success (green), error (red)
- **Component structure**: `components/layout/` (ControlTower, PaneHeader), `components/dashboard/` (PatientQueue, BedBoard, TransportQueue), `components/conversation/` (AgentConversation), `components/timeline/` (EventTimeline)
- **PaneHeader** is reusable: takes LucideIcon, title, optional badge with color variant. Includes subtle accent gradient bar at top.
- **`cn()` utility** in `src/lib/utils.ts` — standard clsx + tailwind-merge pattern for conditional class merging
- **Vite proxy**: `/api` → `http://localhost:8000` configured for dev — aligns with ADR-005 (single container in prod, split dev servers)
- **Path alias**: `@/*` → `./src/*` set in both tsconfig.app.json and vite.config.ts
- **Dark mode only** — `class="dark"` on `<html>`, custom scrollbar styles, `color-scheme: dark`
- Build verified clean, dev server confirmed serving on :5173
