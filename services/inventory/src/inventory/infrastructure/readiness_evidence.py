"""Read independently published commissioning receipts from protected mounts.

No browser-supplied path or URL is opened. Each producer has its own mounted key
and field allowlist. Inventory receives only public verification keys. Signed
receipts bind scope, the immutable input packet
and original evidence bytes. This verifies owner observations, not native support.
"""

import base64
import hashlib
import os
import re
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from inventory.domain.discovery import canonical, digest, shape
from inventory.domain.operator_inputs import FIELDS
from inventory.infrastructure.native_readers import decode, protected


def read_evidence(
    tenant: str,
    site: str,
    packet: str,
    configuration: str | None,
    values: dict[str, Any],
    now: float,
) -> dict[str, Any]:
    location = os.environ.get("INVENTORY_COMMISSIONING_EVIDENCE_FILE")
    if not location:
        return {}
    try:
        config = decode(protected(location, 1048576))
        shape(config, {"schema_version", "producers"})
        if type(config["schema_version"]) is not int or config["schema_version"] != 1:
            raise ValueError
        producers = config["producers"]
        if not isinstance(producers, list) or not 0 <= len(producers) <= 32:
            raise ValueError
        result: dict[str, Any] = {}
        identities: set[str] = set()
        receipt_count, evidence_bytes = 0, 0
        known_fields = {field["id"] for field in FIELDS}
        for producer in producers:
            shape(producer, {"id", "public_key", "expires_at", "fields", "receipts"})
            if (
                not isinstance(producer["id"], str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", producer["id"])
                or producer["id"] in identities
                or not isinstance(producer["fields"], list)
                or not 1 <= len(producer["fields"]) <= 32
                or any(not isinstance(f, str) or f not in known_fields for f in producer["fields"])
                or len(set(producer["fields"])) != len(producer["fields"])
                or not isinstance(producer["receipts"], list)
                or len(producer["receipts"]) > 128
            ):
                raise ValueError
            identities.add(producer["id"])
            receipt_count += len(producer["receipts"])
            if receipt_count > 128:
                raise ValueError
            key = Ed25519PublicKey.from_public_bytes(
                base64.b64decode(producer["public_key"], validate=True)
            )
            if type(producer["expires_at"]) is not int or producer["expires_at"] <= now:
                continue
            for path in producer["receipts"]:
                receipt = decode(protected(path, 262144))
                shape(receipt, {"payload", "signature"})
                payload = receipt["payload"]
                key.verify(
                    base64.b64decode(receipt["signature"], validate=True),
                    b"multi-tenant/commissioning-receipt/v1\x00" + canonical(payload).encode(),
                )
                shape(
                    payload,
                    {
                        "schema_version",
                        "producer_id",
                        "tenant_id",
                        "site_id",
                        "packet_digest",
                        "configuration_digest",
                        "checks",
                    },
                )
                if (
                    type(payload["schema_version"]) is not int
                    or payload["schema_version"] != 1
                    or payload["producer_id"] != producer["id"]
                ):
                    raise ValueError
                if (
                    payload["tenant_id"],
                    payload["site_id"],
                    payload["packet_digest"],
                    payload["configuration_digest"],
                ) != (tenant, site, packet, configuration):
                    continue
                if not isinstance(payload["checks"], list) or len(payload["checks"]) > 32:
                    raise ValueError
                for check in payload["checks"]:
                    shape(
                        check,
                        {
                            "field_id",
                            "value_sha256",
                            "result",
                            "observed_at",
                            "expires_at",
                            "evidence_file",
                            "evidence_sha256",
                        },
                    )
                    field = check["field_id"]
                    if (
                        field not in producer["fields"]
                        or field not in values
                        or field in result
                        or check["value_sha256"] != digest(values[field])
                        or check["result"] not in {"verified", "failed"}
                        or type(check["observed_at"]) is not int
                        or type(check["expires_at"]) is not int
                        or not 0 < check["observed_at"] < check["expires_at"]
                        or not isinstance(check["evidence_sha256"], str)
                        or not re.fullmatch(r"[a-f0-9]{64}", check["evidence_sha256"])
                    ):
                        raise ValueError
                    raw = protected(check["evidence_file"], 8388608)
                    evidence_bytes += len(raw)
                    if evidence_bytes > 33554432:
                        raise ValueError
                    if hashlib.sha256(raw).hexdigest() != check["evidence_sha256"]:
                        raise ValueError
                    result[field] = {
                        "state": check["result"]
                        if check["observed_at"] <= now < check["expires_at"]
                        else "stale",
                        **{k: check[k] for k in ("observed_at", "expires_at", "evidence_sha256")},
                        "expires_at": min(check["expires_at"], producer["expires_at"]),
                    }
        return result
    except Exception:
        # No path, producer credential, report body or another tenant's facts leak.
        return {field: {"state": "unavailable"} for field in values}
