from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(value: bytes | str) -> str:
    if isinstance(value, str): value=value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def digest_json(value: Any) -> str:
    return "sha256:" + sha256_hex(canonical_json_bytes(value))


def derive_key(root: str | bytes, purpose: str) -> bytes:
    kb=root.encode("utf-8") if isinstance(root,str) else root
    return hmac.new(kb,f"mib-service-key-v1|{purpose}".encode(),hashlib.sha256).digest()


def derive_ed25519_private_key(root: str | bytes, purpose: str) -> Ed25519PrivateKey:
    seed=derive_key(root,f"ed25519|{purpose}")
    return Ed25519PrivateKey.from_private_bytes(seed)


def public_key_b64(private_key: Ed25519PrivateKey) -> str:
    raw=private_key.public_key().public_bytes(encoding=serialization.Encoding.Raw,format=serialization.PublicFormat.Raw)
    return base64.b64encode(raw).decode("ascii")


def key_id_from_public_b64(pub_b64: str) -> str:
    return "ed25519:"+sha256_hex(base64.b64decode(pub_b64))[:24]


def sign_json_ed25519(value: Any, private_key: Ed25519PrivateKey, *, context: str) -> dict[str,str]:
    payload_digest=digest_json(value)
    msg=f"{context}|{payload_digest}".encode("utf-8")
    sig=private_key.sign(msg)
    pub=public_key_b64(private_key)
    return {"scheme":"ed25519","context":context,"payload_digest":payload_digest,"signature":base64.b64encode(sig).decode("ascii"),"public_key":pub,"key_id":key_id_from_public_b64(pub)}


def verify_json_ed25519(value: Any, signature: dict[str,Any], *, expected_context: str | None = None, expected_public_key: str | None = None) -> bool:
    try:
        if signature.get("scheme")!="ed25519": return False
        context=str(signature.get("context",""))
        if expected_context is not None and context!=expected_context:return False
        payload_digest=digest_json(value)
        if not hmac.compare_digest(str(signature.get("payload_digest","")),payload_digest):return False
        pub_b64=str(signature["public_key"])
        if expected_public_key is not None and not hmac.compare_digest(pub_b64,expected_public_key):return False
        pub=Ed25519PublicKey.from_public_bytes(base64.b64decode(pub_b64))
        pub.verify(base64.b64decode(signature["signature"]),f"{context}|{payload_digest}".encode("utf-8"))
        return True
    except Exception:
        return False
