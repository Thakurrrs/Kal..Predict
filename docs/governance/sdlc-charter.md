# SDLC Charter

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review), External Advisor (optional)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-24
- Status: Approved

## Purpose
Define mandatory lifecycle stages, stage gates, artifact standards, and release controls for building Kal..Predict safely and reproducibly.

## Lifecycle Stages
1. Discovery
2. Requirements
3. Design
4. Build
5. Verification
6. Release
7. Operate
8. Continuous Improvement

## Stage Gates
- Gate A: Requirements Complete
- Gate B: Architecture Complete
- Gate C: Engineering Ready
- Gate D: Verification Ready
- Gate E: Paper Release Ready
- Gate F: Limited Live Readiness

## Entry and Exit Criteria
- **Gate A exit**
  - PRD approved
  - Scope, non-goals, and acceptance criteria frozen for current iteration
- **Gate B exit**
  - ADR-0001 approved
  - Data contracts versioned
  - Threat model reviewed
- **Gate C exit**
  - API specs finalized
  - Logging fields standardized
  - Error-handling and retry policy approved
- **Gate D exit**
  - Test strategy approved
  - Replay harness defined
  - Brier and calibration pass criteria locked
- **Gate E exit**
  - Paper mode runs end-to-end
  - Risk gates enforced with no bypass path
  - Incident runbook validated by tabletop exercise
- **Gate F exit**
  - Paper metrics stable across required sample
  - No unresolved Sev-1/Sev-2 issues
  - Founder explicit sign-off for limited live

## Approval Workflow
- Product approval: Founder
- Engineering approval: Founder
- Risk/Security approval: Founder
- Release approval: Founder

## Mandatory Artifact Rule
No stage gate can pass unless the gate-critical documents are updated and status-marked in `docs/`.

## Gate Status Interpretation
- **Implemented:** Code and tests for a gate's scope are completed.
- **Passed:** Implemented state plus required evidence, documentation updates, and explicit approver sign-off are recorded.
- Teams must avoid treating "implemented" as equivalent to "passed" in release decisions.

## Definition of Done (Project-Level)
- Requirement is mapped to architecture and test evidence.
- Risk controls are documented and implemented without manual ambiguity.
- Decision outputs are auditable from logs.
- Operational runbooks exist for normal and incident paths.
