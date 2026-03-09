# INFRA-002: Multi-Model Deployment via Array Parameter

- **Author:** Iceman | **Date:** 2026-03-09 | **Status:** Implemented
- **Issue:** #4 (WI-027)

## Decision

Refactored `foundry.bicep` from single-model parameters to an array-based `modelDeployments` parameter with a `@batchSize(1)` loop. This enables adding/removing model deployments by editing `main.bicepparam` without touching module code.

## Deployments

| Model      | SKU            | Capacity (TPM) | Status   |
|------------|----------------|-----------------|----------|
| gpt-5.2    | GlobalStandard | 100K            | Existing |
| gpt-4.1    | GlobalStandard | 50K             | New      |
| gpt-5-mini | GlobalStandard | 50K             | New      |

## Key Design Choices

1. **`@batchSize(1)`** — ARM deploys model deployments sequentially on the same Cognitive Services account to avoid conflicts.
2. **`primaryModelName` param** — Keeps ACA's `MODEL_DEPLOYMENT_NAME` env var pointing to `gpt-5.2` (the production model). Eval harness uses `ALL_MODEL_DEPLOYMENT_NAMES` output to discover all available models.
3. **Model versions are defaults** — Operators must verify availability in their target region via `az cognitiveservices model list`.

## Risks

- Model availability is region-dependent. `gpt-4.1` or `gpt-5-mini` may not be available in all regions with GlobalStandard SKU.
- Total TPM across deployments (200K) may hit subscription quota. Check with `az cognitiveservices usage list`.
