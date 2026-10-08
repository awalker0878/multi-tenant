"""P07 input completeness only. A checked record is never execution authority."""

import re
from typing import Any

from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected, shape

# Stable input IDs map to the existing package/campaign obligations, not new gates.
INPUTS: dict[str, tuple[str, tuple[str, ...], tuple[str, ...]]] = {
    "N01": ("OpenStack platform owner", ("P07.01", "P07.02"), ("Q05.01", "Q05.03")),
    "N02": ("Platform/security owners", ("P07.01",), ("Q05.01",)),
    "N03": ("Security/IAM owners", ("P07.01",), ("Q05.01", "Q05.08")),
    "N04": ("Infrastructure/state owners", ("P07.02",), ("Q05.03", "Q05.08")),
    "N05": ("Infrastructure/resource owners", ("P07.02",), ("Q05.03", "Q05.09")),
    "N06": ("Guest/application owners", ("P07.03",), ("Q05.04",)),
    "N07": ("Network/security owners", ("P07.04",), ("Q05.04", "Q05.07")),
    "N08": ("Allocation/service owners", ("P07.03",), ("Q05.02",)),
    "N09": ("Enterprise service owners", ("P07.03",), ("Q05.05",)),
    "N10": ("Backup/application owners", ("P07.03", "P07.05"), ("Q05.06", "Q05.08")),
    "N11": ("Lifecycle/security owners", ("P07.01", "P07.05"), ("Q05.01", "Q05.08")),
    "N12": ("Governance/retention owners", ("P07.05",), ("Q05.10",)),
    "N13": ("Qualification/Assurance owners", ("P07.06",), ("Q05.01", "Q05.10")),
    "N14": ("SRE/receiving owners", ("P07.01",), ("Q05.01",)),
    "N15": ("Application/security owners", ("P07.04",), ("Q05.06", "Q05.07")),
}
SCOPE_KEYS = {"tenant_id", "site_id", "environment", "resource_id", "endpoint_id", "native_scope"}
BINDING_HASHES = {
    "plan_digest",
    "installed_tuple_sha256",
    "artifact_set_sha256",
    "ownership_sha256",
    "api_contracts_sha256",
    "custody_binding_sha256",
    "service_contracts_sha256",
    "impact_budget_sha256",
    "data_scope_sha256",
}
UNREVIEWED = {"disposition": "NOT_REVIEWED", "reviewer": None, "reviewed_at": None}


def exact_id(value: Any) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}", value) is not None
        and "://" not in value
        and ".." not in value.split("/")
        and value.lower() not in {"all", "any", "unknown", "unrestricted", "latest", "main", "head"}
    )


def sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def timestamp(value: Any) -> bool:
    return type(value) is int and 0 < value < 253402300800


def validate_binding(binding: Any) -> None:
    shape(binding, BINDING_HASHES | {"scope", "campaign_id", "valid_until"})
    shape(binding["scope"], SCOPE_KEYS)
    if (
        not all(exact_id(v) for v in binding["scope"].values())
        or not exact_id(binding["campaign_id"])
        or not all(sha256(binding[k]) for k in BINDING_HASHES)
        or not timestamp(binding["valid_until"])
    ):
        raise Rejected("invalid_commissioning_binding", 422)


def validate_evidence(evidence: Any, binding_hash: str) -> None:
    shape(evidence, {"uri", "sha256", "revision", "level", "binding_sha256"})
    uri, revision = evidence["uri"], evidence["revision"]
    if (
        not isinstance(uri, str)
        or len(uri) > 512
        or re.fullmatch(r"evidence://[A-Za-z0-9_-]+/[A-Za-z0-9._/-]+", uri) is None
        or ".." in uri.split("/")
        or uri.endswith("/")
        or not sha256(evidence["sha256"])
        or not exact_id(revision)
        or "/" in revision
        or ":" in revision
        or revision.lower() in {"current", "master"}
        or evidence["level"] not in {"E0", "E1", "E2", "E3", "E4"}
        or evidence["binding_sha256"] != binding_hash
    ):
        raise Rejected("unbound_commissioning_evidence", 422)


def assess(record: dict[str, Any], now: int) -> dict[str, Any]:
    """Inspect supplied metadata, without resolving evidence or authenticating people."""
    shape(record, {"schema_version", "record_id", "binding", "inputs"})
    if (
        type(record["schema_version"]) is not int
        or record["schema_version"] != 1
        or record["record_id"] != "P07-NATIVE-INPUTS"
        or not timestamp(now)
    ):
        raise Rejected("invalid_commissioning_record", 422)
    binding = record["binding"]
    if binding is not None:
        validate_binding(binding)
    binding_hash = digest(binding) if binding is not None else None
    items = record["inputs"]
    if (
        not isinstance(items, list)
        or len(items) != len(INPUTS)
        or any(not isinstance(i, dict) or not isinstance(i.get("id"), str) for i in items)
        or {i["id"] for i in items} != set(INPUTS)
    ):
        raise Rejected("invalid_commissioning_inventory", 422)
    holds: list[dict[str, Any]] = []
    for item in sorted(items, key=lambda i: i["id"]):
        shape(
            item,
            {
                "id",
                "status",
                "owner_identity",
                "observer_identity",
                "observed_at",
                "expires_at",
                "evidence",
                "review",
            },
        )
        reason = _cell(item, binding_hash, now)
        if reason is None and (binding is None or binding["valid_until"] <= now):
            reason = "campaign_binding_missing_or_expired"
        if reason:
            role, packages, cases = INPUTS[item["id"]]
            holds.append(
                {
                    "input_id": item["id"],
                    "reason": reason,
                    "owner_role": role,
                    "package_ids": list(packages),
                    "case_ids": list(cases),
                }
            )
    return {
        "schema_version": 1,
        "record_valid": True,
        "record_complete": not holds,
        "result": "HELD" if holds else "COMPLETE_REQUIRES_INDEPENDENT_VERIFICATION",
        "binding_sha256": binding_hash,
        "record_sha256": digest(record),
        "evaluated_at": now,
        "holds": holds,
        "native_write_authorized": False,
        "native_qualification_established": False,
        "limitations": [
            "Metadata only; evidence bytes and reviewer identities are not authenticated.",
            "Current authority, operating controls and native observation remain required.",
            "This report cannot be supplied as an execution grant or a native support claim.",
        ],
    }


def _cell(item: dict[str, Any], binding_hash: str | None, now: int) -> str | None:
    if item["status"] == "UNKNOWN":
        if (
            any(
                item[k] is not None
                for k in ("owner_identity", "observer_identity", "observed_at", "expires_at")
            )
            or item["evidence"] != []
            or item["review"] != UNREVIEWED
        ):
            raise Rejected("unknown_commissioning_input_has_observation", 422)
        return "input_not_supplied"
    if (
        item["status"] != "OBSERVED"
        or binding_hash is None
        or not exact_id(item["owner_identity"])
        or not exact_id(item["observer_identity"])
        or not timestamp(item["observed_at"])
        or not timestamp(item["expires_at"])
        or not item["observed_at"] < item["expires_at"]
        or not isinstance(item["evidence"], list)
        or not 1 <= len(item["evidence"]) <= 32
    ):
        raise Rejected("incomplete_commissioning_observation", 422)
    identities: set[str] = set()
    for evidence in item["evidence"]:
        validate_evidence(evidence, binding_hash)
        if evidence["uri"] in identities:
            raise Rejected("duplicate_commissioning_evidence", 422)
        identities.add(evidence["uri"])
    review = item["review"]
    shape(review, {"disposition", "reviewer", "reviewed_at"})
    if review == UNREVIEWED:
        return "input_not_reviewed"
    if (
        review["disposition"] not in {"ACCEPTED", "REJECTED"}
        or not exact_id(review["reviewer"])
        or not timestamp(review["reviewed_at"])
        or not item["observed_at"] <= review["reviewed_at"] <= now
    ):
        raise Rejected("invalid_commissioning_review", 422)
    if item["observed_at"] > now or item["expires_at"] <= now:
        return "input_expired_or_future"
    if review["disposition"] != "ACCEPTED":
        return "input_rejected"
    if review["reviewer"] in {item["owner_identity"], item["observer_identity"]}:
        return "independent_review_missing"
    # Actual site observation and stop/revocation rehearsal cannot inherit E2 simulation.
    if item["id"] in {"N01", "N03", "N11"} and not any(
        e["level"] in {"E3", "E4"} for e in item["evidence"]
    ):
        return "native_observation_missing"
    if item["id"] in {"N01", "N03", "N11", "N13"} and (
        item["owner_identity"] == item["observer_identity"]
    ):
        return "independent_observer_missing"
    return None
