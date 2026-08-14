from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .canonical import digest
from .model import Receipt


def _schema_path() -> Path:
    configured = os.environ.get("AGENTPROOF_RECEIPT_SCHEMA")
    if configured:
        return Path(configured)
    repository_schema = Path(__file__).resolve().parents[2] / "schemas" / "receipt-v1.schema.json"
    if repository_schema.is_file():
        return repository_schema
    packaged_schema = Path(__file__).resolve().parent.parent / "schema_data" / "receipt-v1.schema.json"
    return packaged_schema


def validate_receipt_schema(data: dict[str, Any]) -> tuple[bool, str]:
    try:
        from jsonschema import Draft202012Validator
        schema_path = _schema_path()
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda error: list(error.path))
        if errors:
            return False, "; ".join(error.message for error in errors[:3])
        return True, ""
    except FileNotFoundError:
        return False, "receipt-v1.schema.json not found"
    except ImportError:
        return False, "jsonschema is not installed"
    except (OSError, json.JSONDecodeError) as exc:
        return False, str(exc)
    except (TypeError, ValueError) as exc:
        return False, f"schema-validation-error: {exc}"


def verify_receipt_data(data: dict[str, Any]) -> tuple[bool, str, str]:
    schema_valid, schema_error = validate_receipt_schema(data)
    expected = str(data.get("digest") or data.get("receipt_sha256", ""))
    unsigned = dict(data)
    unsigned.pop("digest", None)
    unsigned.pop("receipt_sha256", None)
    unsigned.pop("signature", None)
    actual = digest(unsigned)
    if not schema_valid:
        return False, expected, "schema-invalid: " + schema_error
    policy = data.get("policy", {}) or {}
    receipt_policy = policy.get("receipt", {}) or {}
    signature = data.get("signature")
    if receipt_policy.get("signature_required") and not signature:
        return False, expected, "signature-required"
    if signature:
        from .sign import verify_signature
        if not verify_signature(unsigned, signature):
            return False, expected, "signature-invalid"
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
