# UI Test Strategy

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-24
- Status: Approved

## Purpose
Define test coverage and acceptance criteria for the read-only React dashboard and paper-only trial controls.

## Test Levels
- Backend API contract tests for `/api/ui/*` routes
- Backend guardrail tests (GET-only enforcement, no side effects)
- Backend trial action contract tests for `/api/trial/*` paper-only mutation routes
- Frontend component tests (rendering, empty state, error state)
- Frontend integration tests (API wiring and page-level data flow)

## Required Test Cases
- `health` endpoint returns required fields and valid timestamps.
- `markets`, `decisions`, and `audit` endpoints honor query params.
- Replay and paper metrics endpoints return deterministic schema.
- Inference health endpoint returns runtime diagnostics schema.
- Trial decision trace endpoint returns typed trace payload.
- Trial manual/auto endpoints return typed error envelopes on validation and gate failures.
- Trial scenario controls endpoint validates bounded dry-run behavior and summary schema.
- Non-GET requests on UI API routes return 405.
- UI pages render:
  - loading state
  - empty data state
  - populated state
  - backend error state
  - PO checklist pass/fail state rendering

## Quality Gates
- UI API contract tests pass 100%.
- Read-only guardrail tests pass 100%.
- Frontend component/integration tests pass 100%.
- No critical lint/type errors in frontend and backend UI modules.

## Acceptance Criteria
- Operator can view health, markets, decisions, performance, and audit data in one dashboard.
- UI never exposes live execution action controls.
- Missing data artifacts do not crash endpoints or UI pages.
- All UI requests are traceable in backend logs.
- Trial page displays inference diagnostics and risk/decision trace context.
- Trial page renders scenario-control section and dry-run status feedback.
- PO checklist page can execute architecture-flow checks in paper mode.

## Evidence
- Backend API test report in test artifacts.
- Frontend test report in UI test artifacts.
- Screenshot set of all five pages with populated or empty-state data.
