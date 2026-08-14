from __future__ import annotations

import json
from pathlib import Path

from .canonical import digest
from .model import Receipt


def verify_receipt_data(data: dict) -> tuple[bool, str, str]:
    expected = str(data.get("digest") or data.get("receipt_sha256", ""))
    unsigned = dict(data)
    unsigned.pop("digest", None)
    unsigned.pop("receipt_sha256", None)
    unsigned.pop("signature", None)
    actual = digest(unsigned)
    return expected == actual, expected, actual


def verify_receipt(path: Path) -> tuple[bool, str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return verify_receipt_data(data)


def load_verified_receipt(path: Path) -> Receipt:
    valid, expected, actual = verify_receipt(path)
    if not valid:
        raise ValueError(f"AP501 Receipt Invalid: expected {expected}, calculated {actual}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return Receipt.from_dict(data)
