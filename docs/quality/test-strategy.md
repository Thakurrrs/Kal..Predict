# Test Strategy

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-23
- Status: Approved

## Test Levels
- Unit tests
- Integration tests
- Replay/backtest tests
- Paper-trading simulation tests

## Quality Gates
- Lint and static checks
- Minimum test pass criteria
- Coverage thresholds
- Replay benchmark thresholds

## Gate Threshold Policy
- Unit/integration suites must pass at 100% for release candidates.
- Coverage target: set and maintain project threshold before Gate E.
- Replay must show improvement over market baseline in agreed metric set.
- Paper simulation must show zero hard risk-gate violations.

## Exit Criteria
- Gate D: test strategy, fixtures, and benchmark protocol approved.
- Gate E: replay and paper evidence recorded, reviewed, and approved.

## Evidence
- Test report location: CI artifacts
- Replay report location: versioned experiment reports
- Approval record: release checklist and gate sign-off notes
