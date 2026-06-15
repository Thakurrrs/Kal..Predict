"""Observation throughput report (Phase 4).

Reads accumulated observations and prints per-category volume: total
observations, distinct days seen, and average markets per day. This is the
decision input for whether/when category model phases and soccer are worth
building. Read-only; makes no network calls and no trades.

Usage:
    python scripts/observation_throughput_report.py
"""

from __future__ import annotations

import sys

from kal_predict.config import load_config
from kal_predict.storage.paper_store import PaperStore


def _format_label(category: str, subcategory: str | None) -> str:
    return f"{category}/{subcategory}" if subcategory else category


def main() -> int:
    config = load_config()
    store = PaperStore(config.paper_data.database_path)
    store.initialize()

    report = store.observation_throughput()
    total = report["total_observations"]

    print("=" * 64)
    print("Observation Throughput Report")
    print("=" * 64)
    if total == 0:
        print("No observations recorded yet. Run the observation scanner first.")
        return 0

    print(f"Window: {report['first_day']} -> {report['last_day']}")
    print(f"Total observations: {total}")
    print("-" * 64)
    header = f"{'category':<22}{'obs':>7}{'days':>6}{'/day':>8}{'supp':>7}{'paper':>7}"
    print(header)
    print("-" * 64)
    for row in report["categories"]:
        label = _format_label(row["category"], row["subcategory"])
        print(
            f"{label:<22}{row['total_observations']:>7}{row['distinct_days']:>6}"
            f"{row['avg_per_day']:>8}{row['supported']:>7}{row['paper_enabled']:>7}"
        )
    print("-" * 64)
    print("Columns: obs=total observations, days=distinct days, /day=avg per day,")
    print("supp=supported parser_status count, paper=paper-enabled count")
    return 0


if __name__ == "__main__":
    sys.exit(main())
