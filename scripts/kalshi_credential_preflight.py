"""Kalshi credential preflight checks (no network calls)."""

from __future__ import annotations

import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from kal_predict.config import load_config


def _validate_rsa_pem(pem: str) -> str | None:
    """Return an error string if the PEM is not a usable RSA private key."""
    try:
        key = serialization.load_pem_private_key(pem.encode("utf-8"), password=None)
    except (ValueError, TypeError):
        return "private key is not valid PEM or is not an unencrypted key"
    if not isinstance(key, rsa.RSAPrivateKey):
        return "private key is not an RSA private key"
    return None


def main() -> int:
    config = load_config()
    kalshi = config.kalshi

    if not kalshi.api_key_id:
        print("ERROR: KALSHI_API_KEY_ID is missing.")
        return 1

    inline_pem = kalshi._normalized_inline_pem()
    if inline_pem:
        error = _validate_rsa_pem(inline_pem)
        if error:
            # Never print key material, only the validation result.
            print(f"ERROR: inline KALSHI_PRIVATE_KEY_PEM invalid: {error}")
            return 1
        print("OK: Kalshi credential preflight passed.")
        print("api_key_id_present=yes")
        print("private_key_source=inline")
        return 0

    if not kalshi.private_key_path:
        print("ERROR: provide KALSHI_PRIVATE_KEY_PEM (inline) or KALSHI_PRIVATE_KEY_PATH.")
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

    error = _validate_rsa_pem(key_path.read_text())
    if error:
        print(f"ERROR: private key at {key_path} invalid: {error}")
        return 1

    print("OK: Kalshi credential preflight passed.")
    print("api_key_id_present=yes")
    print("private_key_source=path")
    print(f"private_key_path={key_path}")
    print(f"private_key_size_bytes={key_size}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
