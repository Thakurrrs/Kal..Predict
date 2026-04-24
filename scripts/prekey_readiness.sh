#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[1/5] Backend tests (pytest -q)"
source venv/bin/activate
pytest -q
deactivate

echo "[2/5] UI dependency install (npm --prefix ui ci)"
npm --prefix ui ci

echo "[3/5] UI tests (npm --prefix ui run test)"
npm --prefix ui run test

echo "[4/5] UI build (npm --prefix ui run build)"
npm --prefix ui run build

echo "[5/5] Runtime smoke probes (requires backend on 127.0.0.1:8030)"
curl -s "http://127.0.0.1:8030/api/ui/health" >/dev/null
curl -s "http://127.0.0.1:8030/api/ui/inference-health" >/dev/null
curl -s "http://127.0.0.1:8030/api/trial/markets?limit=1" >/dev/null

echo "Pre-key readiness checks passed."
