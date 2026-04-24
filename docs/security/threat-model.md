# Threat Model

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-23
- Status: Approved

## Assets
- API keys
- Private signing keys
- Trading decisions
- Audit logs

## Trust Boundaries
- Local machine
- External APIs
- CI/CD environment

## Threat Scenarios
- Secret leakage
- Prompt/data poisoning
- Unauthorized trade execution
- Log tampering

## Controls
- Access control
- Key isolation
- Signed/auditable events
- Alerting and kill switch rules

## Required Mitigations
- All execution paths must be fail-closed when risk or validation checks fail.
- Secrets must be injected at runtime and never persisted in logs.
- Evidence must carry provenance metadata and freshness timestamps.
- Manual kill switch must be available and documented in operations runbook.
- Incident response must include containment-first protocol before root-cause analysis.
