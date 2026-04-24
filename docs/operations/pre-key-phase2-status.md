# Pre-Key Phase 2 Status

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-24
- Status: Approved

## Completed in pre-key mode
- Trial exchange tab with manual and auto paper bets.
- Ollama inference integration with strict parsing and deterministic fallback.
- Inference observability endpoints and metadata in trial market payloads.
- Read-only API contract hardening and deterministic error envelopes.
- Regression tests for malformed model output and trial API abuse edges.

## Scope guardrail
- Current production scope remains weather-focused for phase execution.
- Category expansion (macro/events/politics) is intentionally deferred; only extension-ready contracts/docs are maintained in this phase.

## In progress
- No active in-progress items in pre-key scope; remaining work is Kalshi-key dependent.

## Blocked by Kalshi credentials
- `phase2-kalshi-read`:
  - Requires `KALSHI_API_KEY_ID` and `KALSHI_PRIVATE_KEY_PATH`.
  - Requires authenticated smoke tests (connectivity, auth, retry/backoff behavior).
- `phase2-paper-parity`:
  - Requires real Kalshi read path active to validate decision/risk parity with real market data.

## Unblock criteria
1. Credentials are available and loaded from `.env`.
2. Connectivity smoke checks succeed in read-only mode.
3. Retry/backoff and stale-data checks pass on real reads.
4. Paper mode remains enforced (`EXECUTION_MODE=paper`) during onboarding.
