# Data Contracts

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-23
- Status: Approved

## Contract List
- Market snapshot schema
- Evidence item schema
- Forecast schema
- Decision schema
- Trade intent schema
- Audit event schema

## Contract Rules
- Every contract must include `schemaVersion`.
- Backward compatibility policy must be documented per version change.
- Breaking changes require ADR and migration notes.

## Minimum Fields Per Contract
- **Market snapshot**
  - `marketId`, `timestamp`, `yesBid`, `yesAsk`, `noBid`, `noAsk`, `volume`
- **Evidence item**
  - `evidenceId`, `source`, `url`, `retrievedAt`, `eventTime`, `claim`, `confidenceHint`, `reliabilityScore`
- **Forecast**
  - `forecastId`, `marketId`, `priorProbability`, `modelProbability`, `mixAlpha`, `mixedProbability`, `generatedAt`
- **Decision**
  - `decisionId`, `marketId`, `mixedProbability`, `marketImpliedProbability`, `edge`, `expectedValue`, `riskGateResult`, `decision`
- **Trade intent**
  - `intentId`, `marketId`, `side`, `maxPrice`, `size`, `mode` (paper/live), `createdAt`
- **Audit event**
  - `traceId`, `eventType`, `actor`, `inputRefs`, `outputRef`, `status`, `timestamp`

## Validation Requirements
- Runtime validation: reject invalid payloads with explicit reason codes.
- Test validation: schema fixtures required in unit/integration tests.
- Failure handling: fail-closed for decision/execution paths; log and quarantine malformed events.
