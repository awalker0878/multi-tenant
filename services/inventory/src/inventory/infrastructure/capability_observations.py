"""Project only signed, fresh native observations from an independently enrolled observer."""

import base64
import hashlib
import json
import os
import stat
import time
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from inventory.domain.capability_definitions import DEFINITION_SHA256, DIMENSIONS
from inventory.domain.discovery import Rejected


def checksum(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def protected_document(path: Path) -> dict[str, Any]:
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("protected_path_invalid")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022:
            raise ValueError("protected_file_invalid")
        raw = stream.read(2097153)
    if len(raw) > 2097152:
        raise ValueError("protected_file_bound")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("protected_document_invalid")
    return result


class MountedCapabilityObservations:
    def read(self, base: dict[str, Any]) -> dict[str, Any] | None:
        path = os.environ.get("INVENTORY_CAPABILITY_EVIDENCE_FILE")
        if not path:
            return None
        try:
            state = protected_document(Path(path))
            trust = protected_document(Path(os.environ["INVENTORY_CAPABILITY_TRUST_FILE"]))
            now = int(time.time())
            results = []
            if state["schema_version"] != 1 or trust["schema_version"] != 1:
                raise ValueError
            for decision, envelope in state["records"].items():
                raw = base64.b64decode(envelope["content_base64"], validate=True)
                if len(raw) > 262144 or hashlib.sha256(raw).hexdigest() != envelope["sha256"]:
                    raise ValueError
                observed = json.loads(raw)
                inventory = observed.get("inventory", {})
                if any(
                    inventory.get(k) != base[k]
                    for k in (
                        "tenant_id",
                        "site_id",
                        "endpoint_id",
                        "generation_id",
                        "native_scope",
                    )
                ):
                    continue
                key = trust["keys"][envelope["key_id"]]
                public = serialization.load_pem_public_key(key["public_key_pem"].encode())
                if not isinstance(public, rsa.RSAPublicKey) or public.key_size < 2048:
                    raise ValueError
                public.verify(
                    base64.b64decode(envelope["signature_base64"], validate=True),
                    raw,
                    padding.PKCS1v15(),
                    hashes.SHA256(),
                )
                if (
                    key["role"] != "observer"
                    or observed["subject_id"] != key["subject_id"]
                    or key["expires_at"] <= now
                    or any(
                        key["scope"].get(k) != base[k]
                        for k in ("tenant_id", "site_id", "endpoint_id")
                    )
                    or decision in state.get("suspended", {})
                    or observed["decision_sha256"] != decision
                    or observed["kind"] != "native_conformance"
                    or observed["simulation"] is not False
                    or observed["finalized"] is not True
                    or observed["adapter_conformant"] is not True
                    or observed["definition_sha256"] != DEFINITION_SHA256
                    or inventory["installed_tuple"] != base["installed_tuple"]
                    or type(observed["observed_at"]) is not int
                    or not 0 <= now - observed["observed_at"] <= 60
                    or not now < observed["expires_at"] <= observed["observed_at"] + 120
                    or observed["expires_at"] > key["expires_at"]
                    or set(observed["dimensions"]) != set(DIMENSIONS)
                    or any(observed["cases"].get("dimension:" + d) != "passed" for d in DIMENSIONS)
                ):
                    raise ValueError
                results.append(
                    {
                        "inventory": inventory,
                        "definition_sha256": DEFINITION_SHA256,
                        "source_sha256": envelope["sha256"],
                        "decision_sha256": decision,
                        "scope_sha256": observed["scope_sha256"],
                        "observed_at": observed["observed_at"],
                        "expires_at": observed["expires_at"],
                        "data": observed["snapshot"],
                    }
                )
            if len(results) > 1:
                raise ValueError("capability_observation_conflict")
            return results[0] if results else None
        except (KeyError, TypeError, ValueError, OSError, InvalidSignature):
            raise Rejected("capability_observation_unavailable", 503) from None
