"Read-only observation contracts. A fact is neither a reservation nor authority."

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid5

DIMENSIONS = (
    "installed_identity",
    "compute_placement",
    "storage_datasets",
    "network_vpc",
    "security_edge",
    "guest_image",
    "lifecycle_adoption",
    "mobility",
    "shared_services",
    "resilience_operations",
    "assurance_sovereignty",
)
PLATFORMS = ("openstack", "vmware", "ahv")
KINDS = ("server", "network", "volume", "datastore")
NAMESPACE = UUID("b4359728-538d-4dcf-8180-992e8923b74f")


class Rejected(Exception):
    def __init__(self, reason: str, status: int = 422) -> None:
        super().__init__(reason)
        self.reason = reason
        self.status = status


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def identifier(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        ("[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"), value
    ):
        raise Rejected("invalid_identity")
    return value


def text(value: Any, maximum: int = 200) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise Rejected("invalid_text")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise Rejected("invalid_text")
    return value


def number(value: Any, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise Rejected("invalid_bound")
    return value


def shape(value: Any, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict) or not required <= value.keys():
        raise Rejected("invalid_shape")
    if value.keys() - required - (optional or set()):
        raise Rejected("unknown_field")
    return value


def observation(value: Any, project: str, platform: str) -> dict[str, Any]:
    item = shape(value, {"kind", "native_id", "incarnation", "name", "scope", "facts"})
    if item["kind"] not in KINDS or item["scope"] != project:
        raise Rejected("foreign_native_scope")
    native = text(item["native_id"])
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", native):
        raise Rejected("invalid_native_identity")
    incarnation = item["incarnation"]
    if incarnation is not None:
        text(incarnation)
    text(item["name"], 255)
    facts = shape(item["facts"], set(), {"power", "cpu", "memory_mib", "size_gib", "status"})
    for key, val in facts.items():
        if key in {"cpu", "memory_mib", "size_gib"}:
            number(val, 0, 9007199254740991)
        else:
            text(val, 80)
    if platform not in PLATFORMS:
        raise Rejected("unknown_platform")
    return item


def resource_identity(endpoint: str, epoch: str, kind: str, native: str) -> str:
    # Endpoint UUID, epoch and kind prevent collisions between sites/platform resets.
    return str(uuid5(NAMESPACE, canonical([endpoint, epoch, kind, native])))


def profile(platform: str, installed: dict[str, Any]) -> dict[str, Any]:
    if platform not in PLATFORMS:
        raise Rejected("unknown_platform")
    return {
        "platform": platform,
        "dimensions": {
            key: {
                "state": "UNASSESSED",
                "reason": "native_qualification_required",
                "facts": installed if key == "installed_identity" else {},
                "provenance": "site_policy_declaration"
                if key == "installed_identity"
                else "no_qualified_observation",
            }
            for key in DIMENSIONS
        },
        "native_write_authorized": False,
    }


@dataclass(frozen=True)
class Actor:
    tenant: str
    actor: str
    delegation: str
    action: str
    site: str | None


@dataclass(frozen=True)
class Worker:
    identity: str
    fingerprint: str


@dataclass(frozen=True)
class EnrollmentPolicy:
    """Separately mounted policy. No client request can broaden this scope."""

    policy_id: str
    tenant: str
    site: str
    owner: str
    worker: str
    worker_fingerprint: str
    epoch: str
    platform: str
    native_scope: str
    authority: str
    installed: dict[str, Any]
    streams: list[dict[str, Any]]
    freshness_seconds: int
    requests_per_minute: int
    concurrency: int
    tenant_concurrency: int
    max_pages: int
    expires_at: float
    coverage_reference: str | None
    policy_digest: str

    def public(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "site_id": self.site,
            "owner_id": self.owner,
            "platform": self.platform,
            "native_scope": self.native_scope,
            "epoch": self.epoch,
            "profile": profile(self.platform, self.installed),
            "coverage_reference": self.coverage_reference,
            "policy_digest": self.policy_digest,
        }
