# SDLC Execution Order (No Timeline)

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-24
- Status: Approved

## Objective
Define the exact order of work so the project progresses from documentation to safe execution with no ambiguity.

## Ordered Work Sequence
1. Finalize governance baseline
   - Complete `raci.md` and `sdlc-charter.md`
   - Freeze stage-gate criteria
2. Finalize product requirements
   - Complete `prd-v1.md`
   - Freeze phase-1 market scope and non-goals
3. Finalize architecture decisions
   - Approve `adr-0001-system-boundaries.md`
   - Finalize `data-contracts.md`
4. Finalize engineering specifications
   - Complete `api-spec.md`
   - Freeze integration error/retry policy
5. Finalize security/compliance baseline
   - Approve `threat-model.md`, `secrets-policy.md`
   - Approve `audit-logging-standard.md`, `change-management.md`
6. Finalize quality and operations readiness
   - Approve `test-strategy.md`
   - Approve `runbook-paper-trading.md` and `incident-response.md`
7. Build pre-Kalshi implementation track (before API credentials)
   - Implement provider interfaces for market data and execution
   - Implement mock exchange adapter and synthetic market fixtures
   - Build ingestion, evidence normalization, forecasting, risk gating, execution simulation, and observability against mocks
8. Run pre-Kalshi verification track
   - Unit/integration tests against mock adapter
   - Replay/backtest and calibration checks using offline data
   - Paper-trading dry runs in simulated environment
9. Saturday onboarding gate (credentials available)
   - Add real Kalshi credentials in secure local environment
   - Run auth/connectivity smoke tests in read-only mode
   - Validate logging, risk gating, and fail-closed behavior with real reads
10. Build implementation in order
   - Data ingestion -> evidence normalization -> forecasting -> risk gating -> execution simulator -> observability
11. Run verification in order
   - Unit/integration tests -> replay/backtest -> calibration checks -> paper-trading dry runs
12. Enter controlled operation
   - Paper mode only until release criteria pass
   - Consider limited live only after explicit gate sign-off

## Non-Negotiable Rules
- No coding starts before governance, PRD, and ADR baseline are approved.
- No execution path is allowed without deterministic risk gates.
- No live trading is allowed without paper-mode acceptance.
- Real Kalshi order writes are blocked until Saturday onboarding gate passes.
- "Implemented" gate work does not equal "Passed" gate status until evidence and sign-off are formally recorded.
