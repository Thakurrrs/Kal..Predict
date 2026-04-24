# Secrets Management Policy

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-23
- Status: Approved

## Scope
Covers API keys, private keys, tokens, and credentials used by project systems.

## Requirements
- Never commit secrets to version control.
- Use environment-based secret injection.
- Define rotation intervals and revocation process.
- Restrict access by least privilege.

## Operations
- Provisioning process: generate least-privilege credentials per provider and store in local secure environment file excluded from version control.
- Rotation process: rotate keys on schedule and immediately after suspected exposure.
- Emergency revocation process: revoke compromised key, halt automation, rotate replacements, validate clean restart.
- Audit requirements: maintain key inventory with created date, last rotated date, and owner.
