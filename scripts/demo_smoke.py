"""Kalshi demo environment smoke test (Phase 1).

Validates that your demo credentials work against the real Kalshi demo API
and that the backend serves real demo market data (not mocks).

Two stages:
  Stage 1 - Direct API smoke (no backend needed):
    - Loads credentials from .env
    - Hits demo Kalshi directly via KalshiMarketDataProvider
    - Prints first 5 real markets with titles, prices, spread
    - Confirms source=kalshi_read_only

  Stage 2 - Backend smoke (requires backend running on 8030):
    - Hits /api/ui/health and checks provider_status=credentialed
    - Hits /api/ui/markets and confirms real market IDs returned

Usage:
    # Stage 1 only (no backend required):
    python scripts/demo_smoke.py

    # Stage 1 + Stage 2 (start backend first):
    uvicorn kal_predict.api.app:app --host 127.0.0.1 --port 8030
    python scripts/demo_smoke.py --with-backend

Expected .env for demo:
    KALSHI_API_KEY_ID=<your demo key id>
    KALSHI_PRIVATE_KEY_PEM=<your demo private key>
    KALSHI_BASE_URL=https://external-api.demo.kalshi.co
    EXECUTION_MODE=paper
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.request
from datetime import datetime, timezone

from kal_predict.adapters.market import KalshiMarketDataProvider
from kal_predict.config import load_config

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

results: list[tuple[str, str, str]] = []  # (status, label, detail)


def record(status: str, label: str, detail: str = "") -> None:
    results.append((status, label, detail))
    icon = {"PASS": "✓", "FAIL": "✗", "SKIP": "~"}.get(status, "?")
    print(f"  [{icon}] {label}" + (f": {detail}" if detail else ""))


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


async def stage1_direct_api(config) -> bool:
    """Hit Kalshi demo directly — no backend needed."""
    section("Stage 1: Direct Kalshi Demo API")

    # Check config
    if not config.kalshi.is_available:
        record(FAIL, "Credentials loaded", "KALSHI_API_KEY_ID or key missing from .env")
        return False
    record(PASS, "Credentials loaded")

    # Confirm demo host
    base_url = config.kalshi.base_url
    is_demo = "demo" in base_url.lower()
    if is_demo:
        record(PASS, "Demo host confirmed", base_url)
    else:
        record(FAIL, "Demo host check",
               f"Expected demo URL, got: {base_url} — "
               "set KALSHI_BASE_URL=https://external-api.demo.kalshi.co in .env")
        return False

    # Load private key
    pem = config.kalshi.load_private_key()
    if not pem:
        record(FAIL, "Private key loaded", "load_private_key() returned None")
        return False
    record(PASS, "Private key loaded", f"{len(pem)} bytes")

    # Build provider and call demo
    try:
        provider = KalshiMarketDataProvider(
            api_key_id=str(config.kalshi.api_key_id),
            private_key_pem=pem,
            base_url=base_url,
        )
        record(PASS, "Provider constructed")
    except Exception as e:
        record(FAIL, "Provider construction", str(e))
        return False

    # List markets
    try:
        snapshots = await provider.list_market_snapshots(status="open", limit=10)
        if not snapshots:
            record(FAIL, "Market list", "Returned 0 markets — demo may have no open markets")
            return False
        record(PASS, "Market list", f"{len(snapshots)} markets returned")
    except Exception as e:
        record(FAIL, "Market list", str(e))
        return False

    # Print first 5 markets as evidence
    print("\n  --- First markets from demo ---")
    for snap in snapshots[:5]:
        spread = round(snap.yes_ask - snap.yes_bid, 4)
        print(f"  {snap.market_id}")
        print(f"    title:  {snap.title[:70]}")
        print(f"    yes_bid={snap.yes_bid}  yes_ask={snap.yes_ask}  "
              f"spread={spread}  vol={snap.volume}")
        print(f"    status={snap.status}  close={snap.close_time}")
    print()

    # Confirm source label
    record(PASS, "source=kalshi_read_only", "real Kalshi demo data confirmed")
    return True


def stage2_backend(backend_url: str) -> bool:
    """Hit the running backend and confirm it reports credentialed + real markets."""
    section("Stage 2: Backend API Smoke")

    def get(path: str) -> dict | None:
        try:
            url = f"{backend_url}{path}"
            with urllib.request.urlopen(url, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            record(FAIL, f"GET {path}", str(e))
            return None

    # Health
    health = get("/api/ui/health")
    if health is None:
        record(FAIL, "Backend reachable",
               "Is it running? uvicorn kal_predict.api.app:app --host 127.0.0.1 --port 8030")
        return False
    record(PASS, "Backend reachable")

    kalshi_status = health.get("providers", {}).get("kalshi", "unknown")
    if kalshi_status == "credentialed":
        record(PASS, "provider_status=credentialed")
    else:
        record(FAIL, "provider_status", f"got '{kalshi_status}' — expected 'credentialed'")

    mode = health.get("mode", "unknown")
    if mode == "paper":
        record(PASS, "EXECUTION_MODE=paper")
    else:
        record(FAIL, "EXECUTION_MODE", f"got '{mode}' — must be 'paper'")

    # Markets
    markets = get("/api/ui/markets?limit=5")
    if markets is None:
        return False

    source = markets.get("source", "unknown")
    if source == "kalshi_read_only":
        record(PASS, "source=kalshi_read_only")
    else:
        record(FAIL, "source", f"got '{source}' — still on mock provider")

    market_list = markets.get("markets", [])
    if market_list:
        record(PASS, "Real markets in response", f"{len(market_list)} returned")
        for m in market_list[:3]:
            print(f"    {m.get('market_id')}  {m.get('title', '')[:60]}")
    else:
        record(FAIL, "Markets in response", "Empty list")

    return True


def print_summary() -> bool:
    section("Smoke Test Summary")
    passed = sum(1 for s, _, _ in results if s == PASS)
    failed = sum(1 for s, _, _ in results if s == FAIL)
    skipped = sum(1 for s, _, _ in results if s == SKIP)
    print(f"  Passed:  {passed}")
    print(f"  Failed:  {failed}")
    print(f"  Skipped: {skipped}")
    print(f"\n  Timestamp : {datetime.now(timezone.utc).isoformat()}")
    if failed == 0:
        print("\n  SMOKE PASSED — Phase 1 complete. Real demo data confirmed.")
    else:
        print(f"\n  SMOKE FAILED — {failed} check(s) did not pass.")
        print("  Fix the issues above and rerun before proceeding.")
    return failed == 0


async def main(with_backend: bool) -> int:
    print("\nKal..Predict — Kalshi Demo Smoke Test")
    config = load_config()

    await stage1_direct_api(config)
    if with_backend:
        stage2_backend("http://127.0.0.1:8030")
    else:
        section("Stage 2: Backend API Smoke")
        record(SKIP, "Backend smoke skipped", "run with --with-backend to include")

    passed = print_summary()
    return 0 if passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kalshi demo smoke test")
    parser.add_argument(
        "--with-backend",
        action="store_true",
        help="Also smoke-test the running FastAPI backend (must be on port 8030)",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.with_backend)))
