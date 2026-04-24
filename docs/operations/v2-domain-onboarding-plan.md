# V2 Domain Onboarding Plan (Post-Weather)

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-24
- Status: Approved

## Objective
Prepare controlled expansion from weather-only execution to additional categories after weather baseline remains stable.

## Candidate domains
1. Finance/Economics
2. Politics/Public Events
3. Sports

## Expansion constraints
- Weather remains primary production scope until explicit expansion approval.
- New domain rollout is additive and reversible.
- Risk gates and fail-closed behavior remain deterministic across all domains.
- Paper-only mode remains enforced until relevant gate sign-off.

## Model routing guidance (24GB-safe)
- Keep one supervisory brain model and one fast hands model baseline.
- Add domain-specific prompt/routing policy before adding any new model weights.
- Prefer shared model reuse with domain-specific templates first.
- Introduce additional local models only when latency/accuracy evidence justifies cost.

## Domain onboarding checklist
1. Define domain-specific contract schema deltas (if needed) and update docs.
2. Add domain ingestion source list + reliability filters.
3. Add replay fixtures for the new domain.
4. Add deterministic decision/regression tests for new domain path.
5. Update UI labels/filtering to include the new domain without changing weather defaults.
6. Record evidence run (tests + build + probes) and document gate decision.

## Entry criteria
- Weather replay and paper metrics remain within accepted thresholds.
- No unresolved Sev-1/Sev-2 issues.
- Founder approval to start domain onboarding cycle.
