from __future__ import annotations

from typing import Any

from .canonical import canonical_json


def sign_payload(payload: dict[str, Any], private_key: bytes) -> dict[str, str]:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install cryptography to use Ed25519 signing") from exc
    key = Ed25519PrivateKey.from_private_bytes(private_key)
    signature = key.sign(canonical_json(payload)).hex()
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    return {"algorithm": "Ed25519", "public_key": public, "signature": signature}


def verify_signature(payload: dict[str, Any], signature: dict[str, str]) -> bool:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError:
        return False
    try:
        key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(signature["public_key"]))
        key.verify(bytes.fromhex(signature["signature"]), canonical_json(payload))
        return True
    except (KeyError, ValueError):
        return False
