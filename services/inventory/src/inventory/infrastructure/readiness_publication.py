"""Owner-side publication of existing observations, with a private signing key.

Run separately from Inventory's runtime. Signing does not run a native test, invent
an observation or grant admission. Only an independently enrolled producer is read.
"""

import base64
import hashlib
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from inventory.domain.discovery import canonical, digest, identifier, shape
from inventory.domain.operator_inputs import validate_values
from inventory.domain.readiness import validate_context
from inventory.infrastructure.native_readers import decode, protected


def publish(packet_path: str, report_path: str, producer: str, key_path: str, output: str) -> None:
    packet = decode(protected(packet_path, 1048576))
    report = decode(protected(report_path, 262144))
    record, context = packet["record"], packet["context"]
    validate_context(context)
    validate_values(record["values"])
    identifier(packet["tenant_id"])
    identifier(packet["site_id"])
    body = {
        "values": record["values"],
        "configuration_digest": record["configuration_digest"],
        "context": context,
    }
    if (
        packet.get("native_write_authorized") is not False
        or type(record["revision"]) is not int
        or record["revision"] < 1
        or digest([packet["tenant_id"], packet["site_id"], record["revision"], body])
        != record["digest"]
    ):
        raise ValueError("input_packet_binding_changed")
    shape(
        report,
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
        type(report["schema_version"]) is not int
        or report["schema_version"] != 1
        or report["producer_id"] != producer
        or report["tenant_id"] != packet["tenant_id"]
        or report["site_id"] != packet["site_id"]
        or report["packet_digest"] != record["digest"]
        or report["configuration_digest"] != record["configuration_digest"]
        or not isinstance(report["checks"], list)
        or not 1 <= len(report["checks"]) <= 32
    ):
        raise ValueError("observation_scope_changed")
    seen = set()
    for check in report["checks"]:
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
            field in seen
            or field not in record["values"]
            or check["value_sha256"] != digest(record["values"][field])
            or check["result"] not in {"verified", "failed"}
            or type(check["observed_at"]) is not int
            or type(check["expires_at"]) is not int
            or not 0 < check["observed_at"] < check["expires_at"]
            or hashlib.sha256(protected(check["evidence_file"], 8388608)).hexdigest()
            != check["evidence_sha256"]
        ):
            raise ValueError("observation_binding_changed")
        seen.add(field)
    if Path(key_path).stat().st_mode & 0o077:
        raise ValueError("private_key_permissions")
    key = Ed25519PrivateKey.from_private_bytes(protected(key_path, 32))
    signature = key.sign(b"multi-tenant/commissioning-receipt/v1\x00" + canonical(report).encode())
    envelope: dict[str, Any] = {
        "payload": report,
        "signature": base64.b64encode(signature).decode(),
    }
    destination = Path(output)
    if not destination.is_absolute() or any(p.is_symlink() for p in destination.parents):
        raise ValueError("receipt_destination_invalid")
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(canonical(envelope).encode() + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
