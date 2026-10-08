"""A declaration cannot replace a current evidence-bound native snapshot."""

from typing import Any

from planning.domain.capability_definitions import DEFINITION_SHA256
from planning.domain.model import digest


def snapshot(
    destination: dict[str, Any], qualification: dict[str, Any], now: int
) -> dict[str, Any] | None:
    current = destination.get("capability_snapshot")
    receipt = qualification.get("verification") or {}
    if not isinstance(current, dict) or (
        current.get("definition_sha256") != DEFINITION_SHA256
        or current.get("source_sha256") != receipt.get("runtime_sha256")
        or current.get("decision_sha256") != receipt.get("decision_sha256")
        or current.get("scope_sha256") != digest(qualification.get("scope"))
        or type(current.get("observed_at")) is not int
        or not 0 <= now - current["observed_at"] <= 60
        or type(current.get("expires_at")) is not int
        or not now < current["expires_at"] <= current["observed_at"] + 120
    ):
        return None
    return dict(current["data"])


def inventory_digest(destination: dict[str, Any]) -> str:
    """Exclude fetch metadata, retaining every measured semantic value and authority."""
    data = {k: v for k, v in destination.items() if k != "expires_at"}
    current = data.get("capability_snapshot")
    if isinstance(current, dict):
        data["capability_snapshot"] = {
            k: v for k, v in current.items()
            if k not in {"source_sha256", "observed_at", "expires_at"}
        }
    return digest(data)
