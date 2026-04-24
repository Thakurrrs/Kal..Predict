# Kalshi Credential Onboarding Smoke Runbook

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-24
- Status: Approved

## Purpose
Define the exact first smoke-test sequence to run once Kalshi credentials are available, while keeping the system paper-only.

## Preconditions
- `EXECUTION_MODE=paper` is set.
- Backend and UI dependencies are installed.
- Private key exists on local disk and is excluded from version control.
- `.env` includes:
  - `KALSHI_API_KEY_ID`
  - `KALSHI_PRIVATE_KEY_PATH`

## Step 0 - Pre-key readiness gate
Run this before touching Kalshi onboarding:

```bash
bash scripts/prekey_readiness.sh
```

All checks must pass.

## Step 1 - Credential preflight
Validate that credentials are loaded and key file exists:

```bash
python scripts/kalshi_credential_preflight.py
```

Expected outcome: `OK` with key file metadata (path + size, no secret content).

## Step 2 - Start backend in paper mode

```bash
source venv/bin/activate
uvicorn kal_predict.api.app:app --host 127.0.0.1 --port 8030 --reload
```

## Step 3 - Read-only smoke probes
In a second terminal:

```bash
curl -s "http://127.0.0.1:8030/api/ui/health"
curl -s "http://127.0.0.1:8030/api/ui/inference-health"
curl -s "http://127.0.0.1:8030/api/trial/markets?limit=1"
```

Expected outcome:
- Endpoints return valid JSON.
- No unhandled exceptions.
- `EXECUTION_MODE` remains paper.

## Step 4 - Capture evidence
Record:
- command outputs,
- timestamp,
- branch + commit hash,
- pass/fail decision and any follow-ups.

Append to `docs/quality/pre-key-phase2-evidence-pack.md` (or successor evidence doc for key-onboarding session).

## Failure policy
- Any failed probe or credential validation means onboarding is paused.
- Fix issue, rerun full smoke sequence, and only then proceed.
- No live-write enablement during smoke phase.
