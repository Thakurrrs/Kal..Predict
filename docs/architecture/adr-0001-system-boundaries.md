# ADR-0001: System Boundaries

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-23
- Status: Approved

## Context
The project separates strategic reasoning from deterministic execution to improve safety and auditability.

## Decision
- Use one Supervisory Brain and multiple specialized Hands.
- Use deterministic modules for risk checks and execution path.
- Restrict LLM outputs to forecast/evidence interpretation only.
- Require every action to pass hard gate checks before execution intent.
- Start with weather-focused hands and expand only after metrics pass.

## Consequences
- Positive:
  - Stronger auditability and operational control.
  - Better modular testing and SDLC ownership alignment.
  - Lower chance of hallucinated direct actions.
- Trade-offs:
  - More orchestration and interface management overhead.
  - Requires disciplined schema/version governance.

## Alternatives Considered
- Monolithic single-agent architecture: rejected due to poor control and weak audit boundaries.
- Fully rules-only strategy: rejected for insufficient adaptability to evolving evidence.
- Autonomous per-category traders without supervisor: rejected for inconsistent portfolio-level risk.

## Follow-Up Actions
- Define typed interfaces between supervisory and category agents.
- Finalize event schema, trace IDs, and state handoff contracts.
- Document deterministic risk gate contract and fail-closed behavior.
- Add architecture diagram in next ADR if topology changes.
