"""Complete, artifact-bound guest, service, security and dataset acceptance contract."""

import re
from typing import Any

from lifecycle.domain.admission import digest
from lifecycle.domain.capability_definitions import PLATFORMS
from lifecycle.domain.execution import Rejected
from lifecycle.domain.execution import identity as identifier
from lifecycle.domain.native_workflow import checksum as sha
from lifecycle.domain.native_workflow import exact as shape

SERVICES = {"ipam", "dns", "identity", "time", "trust", "logging", "monitoring", "backup"}
GUEST = {"boot", "drivers", "storage", "network", "identity"}


def validate_outcomes(o: dict[str, Any], bound: dict[str, Any], artifacts: dict[str, Any]) -> None:
    shape(
        o,
        {
            "source_platform",
            "target_platform",
            "owner_inputs_sha256",
            "route_sha256",
            "guest_profile_sha256",
            "guest",
            "services",
            "security",
            "datasets",
        },
    )
    if (
        o["source_platform"] not in PLATFORMS
        or o["target_platform"] not in PLATFORMS
        or o["owner_inputs_sha256"] != bound["owner_inputs_sha256"]
        or o["guest_profile_sha256"] != artifacts["guest"]
    ):
        raise Rejected("migration_outcome_scope_changed", 423)
    sha(o["route_sha256"])
    for collection, keys in (("guest", GUEST), ("services", SERVICES)):
        for value in shape(o[collection], keys).values():
            sha(value)
    rows = o["security"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 128:
        raise Rejected("migration_security_mapping_required", 422)
    seen = set()
    for row in rows:
        shape(row, {"id", "source_rule_sha256", "target_rule_sha256", "semantics_sha256"})
        if (
            not isinstance(row["id"], str)
            or not re.fullmatch(r"[a-z0-9_-]{1,60}", row["id"])
            or row["id"] in seen
        ):
            raise Rejected("migration_security_mapping_ambiguous", 422)
        seen.add(row["id"])
        for key in ("source_rule_sha256", "target_rule_sha256", "semantics_sha256"):
            sha(row[key])
    datasets = o["datasets"]
    if not isinstance(datasets, dict) or set(datasets) != set(bound["datasets"]):
        raise Rejected("migration_dataset_validation_incomplete", 422)
    for key, value in datasets.items():
        identifier(key)
        sha(value)
    # Fingerprinting requires a finite, canonical JSON record.
    digest(o)


def requirements(o: dict[str, Any]) -> dict[str, str]:
    return {
        **{"guest_" + k: v for k, v in o["guest"].items()},
        **{"service_" + k: v for k, v in o["services"].items()},
        **{"dataset_" + k: v for k, v in o["datasets"].items()},
        **{"security_rule_" + r["id"]: digest(r) for r in o["security"]},
    }
