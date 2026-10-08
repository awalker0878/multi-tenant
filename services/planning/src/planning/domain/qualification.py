"""Resolved owner provenance is bound to exact immutable record bytes and definition."""

from typing import Any

from planning.domain.capability_definitions import DEFINITION_SHA256
from planning.domain.model import digest


def verified(qualification: dict[str, Any], now: int) -> bool:
    verification = qualification.get("verification") or {}
    record = {k: v for k, v in qualification.items() if k != "verification"}
    return (
        qualification.get("version") == 2
        and verification.get("valid") is True
        and verification.get("definition_sha256") == DEFINITION_SHA256
        and verification.get("record_sha256") == digest(record)
        and type(verification.get("resolved_at")) is int
        and 0 <= now - verification["resolved_at"] <= 5
        and verification.get("expires_at", 0) > now
    )


def binding_digest(qualification: dict[str, Any]) -> str:
    """Pin reviewed record bytes; independently recheck current runtime on every read."""
    receipt = qualification.get("verification") or {}
    record = {k: v for k, v in qualification.items() if k != "verification"}
    return digest(
        {
            "record": record,
            "valid": receipt.get("valid"),
            "definition_sha256": receipt.get("definition_sha256"),
            "decision_sha256": receipt.get("decision_sha256"),
            "acceptance_sha256": receipt.get("acceptance_sha256"),
        }
    )
