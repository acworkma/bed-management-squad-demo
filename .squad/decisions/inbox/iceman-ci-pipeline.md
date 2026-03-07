### 2026-03-07: CI Pipeline — Dual-Job Lint+Test
**By:** Iceman
**What:** Replaced placeholder `squad-ci.yml` with a proper CI pipeline: parallel Python (pytest + ruff) and Frontend (tsc + vite build) jobs. Ruff lint is non-blocking (`continue-on-error`) until the 19 pre-existing lint issues are resolved. Triggers on PRs to main and pushes to main. Deploy workflow untouched.
**Why:** WI-019 requirement. The old workflow ran `node --test test/*.test.js` which doesn't match this project at all. New pipeline validates both halves of the stack on every PR.
