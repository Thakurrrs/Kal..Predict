# Product Requirements Document (PRD) v1

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-24
- Status: Approved

## Problem Statement
Prediction market contracts are frequently mispriced for short windows when new evidence appears faster than the market can fully reprice. A system is needed to ingest real-time evidence, generate calibrated probabilities, and act through deterministic risk controls.

## Goals
- Build a safety-first event-driven prediction system for Kalshi-style binary markets.
- Achieve measurable improvement over market baseline in calibration quality (Brier score).
- Enforce deterministic risk gates before any execution decision.
- Run stable paper trading before any limited live rollout.

## Non-Goals
- Fully autonomous high-frequency execution in phase 1.
- Multi-asset support outside defined prediction market scope.
- Maximizing trade count over risk-adjusted quality.

## Target Users
- Founder/operator (primary)
- Future quant/engineering collaborators (secondary)

## Scope (Phase 1)
- Domain: weather prediction contracts first.
- Data: Kalshi market data, NWS weather data, and web evidence sources.
- Mode: replay and paper trading only for acceptance.
- Agent topology: one supervisory brain plus specialized category hands.
- Build sequencing constraint: pre-Saturday development uses mock exchange integration until Kalshi credentials are available.

## Functional Requirements
- Ingest market snapshots and external evidence.
- Normalize evidence with source and timestamp metadata.
- Produce market-conditioned probability updates.
- Mix market prior and model posterior using controlled alpha.
- Compute decision gap and expected value after fees/slippage assumptions.
- Apply hard risk gates before generating trade intent.
- Log complete decision traces with correlation IDs.

## Non-Functional Requirements
- Deterministic risk and execution code paths.
- Reproducible runs from stored inputs and configs.
- Audit-grade structured logs for every decision.
- Operational recovery from interruption with preserved state.

## Success Metrics
- Forecast quality:
  - Brier score better than market baseline over replay sample.
- Calibration quality:
  - Reliability curve within defined error tolerance across probability bins.
- Risk compliance:
  - Zero violations of configured hard limits in paper mode.
- Operational reliability:
  - Stable paper loop with recoverable restarts and complete logs.

## Acceptance Criteria
- Gate A/B/C/D criteria are satisfied and formally passed.
- Gate E implementation criteria are satisfied in code/tests; formal Gate E pass requires recorded evidence and explicit sign-off per SDLC charter.
- Replay benchmark passes pre-defined thresholds.
- Paper-trading run demonstrates risk-compliant operation end-to-end.
- Every trade recommendation is explainable from evidence, model output, and gate results.
- Saturday onboarding gate passes before real Kalshi write flows are enabled.

## Risks and Assumptions
- Assumes external APIs remain available and terms-compliant.
- Assumes evidence quality can be filtered enough to reduce noise.
- Main risks: overfitting replay data, model overconfidence, and hidden execution friction.

## Dependencies
- Kalshi API access and credentials
- NWS API access
- Search/retrieval API access
- Local model runtime (Ollama) for prototype inference

## Interim Plan Until Credentials Arrive
- Use mock market data and execution adapters for all build/test workflows.
- Complete all non-Kalshi core modules and verification before Saturday.
- On Saturday, run connectivity/auth smoke tests and keep write path disabled until checks pass.
