"""Kalshi credential preflight checks (no network calls)."""

from __future__ import annotations

from pathlib import Path
import sys

from kal_predict.config import load_config


def main() -> int:
    config = load_config()
    kalshi = config.kalshi

    if not kalshi.api_key_id:
        print("ERROR: KALSHI_API_KEY_ID is missing.")
        return 1

    if not kalshi.private_key_path:
        print("ERROR: KALSHI_PRIVATE_KEY_PATH is missing.")
        return 1

    key_path = Path(kalshi.private_key_path).expanduser()
    if not key_path.exists():
        print(f"ERROR: private key file not found at {key_path}")
        return 1

    if not key_path.is_file():
        print(f"ERROR: private key path is not a file: {key_path}")
        return 1

    key_size = key_path.stat().st_size
    if key_size == 0:
        print(f"ERROR: private key file is empty: {key_path}")
        return 1

    print("OK: Kalshi credential preflight passed.")
    print(f"api_key_id_present=yes")
    print(f"private_key_path={key_path}")
    print(f"private_key_size_bytes={key_size}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
