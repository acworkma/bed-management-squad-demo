### 2026-03-07: Infra decisions — Iceman

**By:** Iceman (DevOps/Infra)

**What:**
- AI Services account uses `disableLocalAuth: true` — Entra ID auth only, no API keys anywhere. Managed identity on the Container App gets `Cognitive Services OpenAI User` role.
- ACR uses `adminUserEnabled: false` — container app pulls via managed identity with `AcrPull` role.
- ACA environment connected to Log Analytics; App Insights connection string passed as env var for application-level telemetry.
- CI/CD uses OIDC federated credentials (no stored secrets for Azure auth). Requires `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` in GitHub secrets.
- Container resources kept minimal for demo: 0.5 CPU, 1Gi memory, scale 0-1.

**Why:** Security best practices (keyless auth), cost efficiency (demo scale), and observability from day one.
