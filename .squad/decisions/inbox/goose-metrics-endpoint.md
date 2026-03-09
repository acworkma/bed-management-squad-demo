# Decision: Metrics endpoint returns 200 with message for empty state

**Author:** Goose | **Date:** 2026-03-09 | **Context:** WI-025

## Decision
`GET /api/metrics` and `GET /api/metrics/history` return HTTP 200 with `{"message": "No scenario runs recorded yet"}` when no metrics exist, rather than 404.

## Rationale
Consistent with the demo's approach — the endpoint exists and works, the resource collection is simply empty. The frontend can check for the `message` key to distinguish empty state from actual data. Using 404 would imply the route doesn't exist, which is misleading.

## Impact
Frontend consumers should check for the `message` key in responses to detect empty state.
