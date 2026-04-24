# ADR-0002: Read-Only UI Dashboard

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-23
- Status: Approved

## Context
Kal..Predict currently operates as a headless backend with logs, replay artifacts, and paper-mode outputs. Operators need visibility into health, decisions, and performance without introducing execution risk.

## Decision
- Introduce a read-only web dashboard using React (Next.js App Router).
- Expose UI data through backend read-only API endpoints.
- Restrict `/api/ui/*` routes to GET-only behavior.
- Allow paper-only operator actions under `/api/trial/*` for pre-key simulation:
  - manual paper bets
  - auto paper bets
  - bounded scenario runs
- Keep live execution controls out of scope for this phase.
- Display data from runtime artifacts and service summaries (heartbeat, decisions, replay metrics, audit events).

## Consequences
- Positive:
  - Faster operational insight and debugging through one dashboard.
  - Better observability for Gate E/F evidence and daily operations.
  - Lower risk than adding mutable operator controls early.
- Trade-offs:
  - Adds frontend and API maintenance overhead.
  - Requires schema and contract version discipline between backend and UI.

## Alternatives Considered
- Streamlit dashboard: rejected for long-term flexibility and component control.
- Server-rendered Python templates only: rejected due to weaker frontend scalability.
- Full operator console with controls: rejected for this phase due to safety risk.

## Guardrails
- `/api/ui/*` endpoints MUST remain read-only.
- No endpoint in `/api/ui/*` may trigger execution side effects.
- `/api/trial/*` endpoints MUST remain paper-only and must never route to live execution.
- Any future mutable UI action requires a new ADR and stage-gate review.

## Follow-Up Actions
- Define endpoint response contracts in `docs/engineering/ui-api-spec.md`.
- Define UI-specific quality gates in `docs/quality/ui-test-strategy.md`.
- Implement API contract tests and component tests before UI sign-off.
