# Repo Verification Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the concrete repo-health findings from the June 13 verification pass without enabling autonomous or live trading.

**Architecture:** Fix the audit-critical persistence defect first, restore the UI API/type contract needed by the existing dashboard pages, then clean Python lint and type-check debt in focused batches. Each task is independently testable and should be committed separately.

**Tech Stack:** Python 3.11, pytest, Ruff, mypy, SQLite, Next.js 14, React 18, TypeScript, Vitest.

---

## File Structure

Modify:

- `src/kal_predict/storage/paper_store.py`  
  Store real ISO8601 decision creation timestamps instead of trace IDs.

- `tests/storage/test_paper_store.py`  
  Add a regression test that reads the stored `decisions.created_at` value.

- `ui/src/lib/api.ts`  
  Restore the frontend API client used by app pages.

- `ui/src/lib/types.ts`  
  Restore shared UI response and DTO types used by app pages.

- `ui/src/app/trial/page.test.tsx`  
  Import the mocked API module through the same alias used by the page.

- `.gitignore`  
  Allow `ui/src/lib` source files to be tracked and ignore TypeScript build info.

- `ui/tsconfig.json`  
  Include Vitest global types so test files type-check with the project.

- Python files reported by `ruff check src tests` and `mypy src`  
  Clean in targeted follow-up commits after functional blockers are fixed.

---

## Task 1: Fix PaperStore Decision Timestamps

**Files:**
- Modify: `tests/storage/test_paper_store.py`
- Modify: `src/kal_predict/storage/paper_store.py`

- [x] **Step 1: Write failing regression test**

Add this test after `test_record_decision_is_idempotent_by_decision_id`:

```python
def test_record_decision_stores_created_at_timestamp(tmp_path):
    store = PaperStore(tmp_path / "paper.db")
    store.initialize()

    store.record_decision(make_decision())

    with store._connect() as connection:
        row = connection.execute("SELECT created_at FROM decisions").fetchone()

    assert row[0] != "trace-1"
    assert row[0].endswith("+00:00")
```

- [x] **Step 2: Run test red**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m pytest tests/storage/test_paper_store.py::test_record_decision_stores_created_at_timestamp -q -p no:cacheprovider --basetemp=.pytest-tmp
```

Expected: failure because `created_at` is currently `trace-1`.

- [x] **Step 3: Implement minimal timestamp fix**

In `src/kal_predict/storage/paper_store.py`, import UTC clock helpers:

```python
from datetime import datetime, timezone
```

In `_record_decision`, replace the final inserted value:

```python
datetime.now(timezone.utc).isoformat(),
```

- [x] **Step 4: Run storage tests green**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m pytest tests/storage/test_paper_store.py -q -p no:cacheprovider --basetemp=.pytest-tmp
```

Expected: all storage tests pass.

- [x] **Step 5: Commit**

Run:

```powershell
git add src/kal_predict/storage/paper_store.py tests/storage/test_paper_store.py docs/superpowers/plans/2026-06-13-repo-verification-cleanup.md
git commit -m "fix: store paper decision timestamps"
```

---

## Task 2: Restore UI API Contract

**Files:**
- Create: `ui/src/lib/api.ts`
- Create: `ui/src/lib/types.ts`
- Modify: `ui/src/app/trial/page.test.tsx`

- [x] **Step 1: Run UI tests red**

Run:

```powershell
npm.cmd --prefix ui run test
```

Expected: `src/app/trial/page.test.tsx` fails to resolve `../../lib/api` or pages fail to resolve `@/lib/api`.

- [x] **Step 2: Add shared UI types**

Create `ui/src/lib/types.ts` with exported interfaces for health, markets, metrics, audit, decisions, trial markets, trial book, and trial decision traces used by the current pages.

- [x] **Step 3: Add API client**

Create `ui/src/lib/api.ts` with `fetchJson()` and exported functions:

```typescript
fetchHealth
fetchMarkets
fetchPaperMetrics
fetchReplayMetrics
fetchAudit
fetchDecisions
fetchTrialMarkets
fetchTrialBook
fetchTrialDecisionTrace
placeTrialManualBet
placeTrialAutoBet
runTrialScenarios
```

- [x] **Step 4: Fix trial test import**

Change:

```typescript
import * as api from "../../lib/api";
```

to:

```typescript
import * as api from "@/lib/api";
```

- [x] **Step 5: Run UI tests and TypeScript**

Run:

```powershell
npm.cmd --prefix ui run test
npx.cmd --prefix ui tsc --noEmit --project ui/tsconfig.json
```

Expected: UI tests pass and TypeScript reports no project errors.

- [x] **Step 6: Commit**

Run:

```powershell
git add ui/src/lib/api.ts ui/src/lib/types.ts ui/src/app/trial/page.test.tsx docs/superpowers/plans/2026-06-13-repo-verification-cleanup.md
git commit -m "fix: restore ui api contract"
```

---

## Task 3: Clean Python Ruff Findings

**Files:**
- Modify only files reported by `.\.venv\Scripts\ruff.exe check src tests`

- [x] **Step 1: Run Ruff red**

Run:

```powershell
.\.venv\Scripts\ruff.exe check src tests
```

Expected before this task: import-order and line-length failures.

- [x] **Step 2: Apply mechanical formatting**

Run:

```powershell
.\.venv\Scripts\ruff.exe check src tests --fix
```

Then manually wrap any remaining `E501` lines.

- [x] **Step 3: Run Ruff green**

Run:

```powershell
.\.venv\Scripts\ruff.exe check src tests
```

Expected: `All checks passed!`

- [x] **Step 4: Commit**

Run:

```powershell
git add src tests docs/superpowers/plans/2026-06-13-repo-verification-cleanup.md
git commit -m "chore: clean python lint findings"
```

---

## Task 4: Clean Python Mypy Findings

**Files:**
- Modify: `src/kal_predict/config.py`
- Modify: `src/kal_predict/models.py`
- Modify: `src/kal_predict/research/weather.py`
- Modify: `src/kal_predict/research/economics.py`
- Modify: `src/kal_predict/adapters/market.py`
- Modify: `src/kal_predict/services/ui_data.py`
- Modify: `src/kal_predict/api/routes.py`
- Modify: `src/kal_predict/api/app.py`
- Modify tests only if type-only test imports are required.

- [x] **Step 1: Run mypy red**

Run:

```powershell
.\.venv\Scripts\mypy.exe src
```

Expected before this task: type errors in the listed files.

- [x] **Step 2: Fix settings config typing**

Use `SettingsConfigDict` from `pydantic_settings` for `BaseSettings` classes in `config.py` instead of `ConfigDict`.

- [x] **Step 3: Fix model computed field ordering and long line**

In `models.py`, use the Pydantic-supported decorator order for computed properties and wrap the long `skip_reason` field.

- [x] **Step 4: Add precise parsed metadata types**

In weather/economics fetchers, replace broad `dict[str, object]` parser return access with typed helper values or casts so mypy can prove metadata and deadline types.

- [x] **Step 5: Fix remaining adapter/API/service typing**

Narrow object values before numeric operations, annotate FastAPI app handlers, and align route return annotations with `JSONResponse` where needed.

- [x] **Step 6: Run mypy green**

Run:

```powershell
.\.venv\Scripts\mypy.exe src
```

Expected: no type errors.

- [x] **Step 7: Run full Python verification and commit**

Run:

```powershell
.\.venv\Scripts\ruff.exe check src tests
$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.pytest-tmp
```

Commit:

```powershell
git add src tests docs/superpowers/plans/2026-06-13-repo-verification-cleanup.md
git commit -m "chore: clean python type findings"
```

---

## Task 5: Record Dependency Audit Follow-Up

**Files:**
- Modify: `docs/superpowers/plans/2026-06-13-repo-verification-cleanup.md`
- Optionally modify: `ui/package-lock.json`, `ui/package.json` only if a low-risk patch update resolves vulnerabilities without breaking tests.

- [x] **Step 1: Run npm audit**

Run:

```powershell
npm.cmd --prefix ui audit
```

Expected: either a vulnerability report or registry failure that must be recorded in this plan.

- [x] **Step 2: Decide fix versus follow-up**

If `npm audit fix` changes only patch/minor locked transitive packages and UI tests still pass, commit it. If it requires breaking upgrades, leave the lockfile unchanged and add a follow-up note.

Result: `npm audit fix` updated the transitive dev dependency `ws` from `8.20.0` to `8.21.0` in `ui/package-lock.json`. The remaining audit findings require `npm audit fix --force`, which would install breaking upgrades (`next@16.2.9` and `vitest@4.1.8`), so those upgrades were not applied in this cleanup task.

- [x] **Step 3: Final verification**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.pytest-tmp
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\mypy.exe src
npm.cmd --prefix ui run test
npx.cmd --prefix ui tsc --noEmit --project ui/tsconfig.json
```

Expected: all required verification commands pass, or remaining dependency-audit risk is explicitly documented.

Result: Python tests, Ruff, mypy, UI tests, and TypeScript all passed. `npm audit` still reports 7 vulnerabilities that require breaking framework/test-runner upgrades; follow-up should plan and test the Next.js/Vitest upgrade separately.
