"""Protected tranche selection; qualification is always read from Assurance custody."""

import os
import stat
from pathlib import Path
from typing import Any

from planning.domain.model import Actor, Rejected, decode, digest, identifier, shape
from planning.infrastructure.owners import request


def selected_tranche(actor: Actor, site: str) -> dict[str, Any]:
    try:
        path = Path(os.environ["PLANNING_MIGRATION_SUPPORT_FILE"])
        if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022 or info.st_size > 2097152:
                raise ValueError
            document = shape(decode(stream.read(2097153)), {"schema_version", "assignments"})
        if document["schema_version"] != 1 or not isinstance(document["assignments"], list):
            raise ValueError
        if len(document["assignments"]) > 256:
            raise ValueError
        expected = {
            "tenant_id": actor.tenant,
            "site_id": identifier(site),
            "resource_id": actor.application,
            "environment": actor.environment,
        }
        matches = []
        for row in document["assignments"]:
            shape(row, {"scope", "tranche"})
            shape(row["scope"], set(expected))
            if row["scope"] == expected:
                matches.append(row["tranche"])
        if len(matches) != 1:
            raise Rejected("migration_support_scope_unassigned", 423)
        return dict(matches[0])
    except Rejected:
        raise
    except (KeyError, TypeError, ValueError, OSError):
        raise Rejected("migration_support_unavailable", 503) from None


def qualification_records(
    actor: Actor, site: str, selected: dict[str, Any]
) -> list[dict[str, Any]]:
    scope = {
        "tenant_id": actor.tenant,
        "site_id": site,
        "resource_id": actor.application,
        "environment": actor.environment,
    }
    result = request(
        "ASSURANCE",
        "POST",
        f"/v1/tenants/{actor.tenant}/migration-qualifications",
        {
            "scope": scope,
            "tranche_sha256": digest(selected),
            "release_sha256": selected["release_sha256"],
        },
        schema_name="migration-support-v1",
    )
    if (
        result["scope"] != scope
        or result["tranche_sha256"] != digest(selected)
        or (result["release_sha256"] != selected["release_sha256"])
    ):
        raise Rejected("migration_support_scope_changed", 423)
    return list(result["records"])


def api_capability_records(
    actor: Actor, site: str, route: dict[str, Any],
) -> dict[str, Any] | None:
    """Read only independently reviewed API evidence from Assurance custody.

    The selected route is not a source of evidence and never supplies a
    browser-provided native qualification. The exact owner assignment is
    re-read, so a changed tranche or revoked E3/E4 result fails closed.
    """
    selected = selected_tranche(actor, site)
    from planning.domain.expansion import tranche

    tranche(selected)
    if sum(1 for item in selected["routes"] if digest(item) == digest(route)) != 1:
        raise Rejected("migration_api_route_unassigned", 423)
    scope = {
        "tenant_id": actor.tenant,
        "site_id": identifier(site),
        "resource_id": actor.application,
        "environment": actor.environment,
    }
    response = request(
        "ASSURANCE",
        "POST",
        f"/v1/tenants/{actor.tenant}/migration-qualifications",
        {
            "scope": scope,
            "tranche_sha256": digest(selected),
            "release_sha256": selected["release_sha256"],
        },
        schema_name="migration-support-v1",
    )
    if (
        response["scope"] != scope
        or response["tranche_sha256"] != digest(selected)
        or response["release_sha256"] != selected["release_sha256"]
    ):
        raise Rejected("migration_api_evidence_owner_changed", 423)
    matches = response.get("api_evidence", {})
    if not isinstance(matches, dict) or len(matches) > 512:
        raise Rejected("migration_api_evidence_invalid", 423)
    return matches.get(digest(route))


def current_application_flow_proof(
    actor: Actor, site: str, saved: dict[str, Any], now: int,
    binding: dict[str, Any],
) -> None:
    """Service-only fresh E4 gate, independent of saved Console approval.

    Catalogue confirms the current published source revision. Assurance must
    independently resolve an E4 runtime-qualified, exact-scope and exact-
    selection evidence record with current allow/deny/return/isolation probes.
    A mounted registry record alone cannot grant migration admission.
    """
    from planning.domain.expansion import tranche

    payload = saved["payload"]
    current = request(
        "CATALOGUE", "GET",
        f"/internal/tenants/{actor.tenant}/applications/{actor.application}"
        f"/environments/{actor.environment}/current-planning-intent",
        schema_name="catalogue-current-v1",
    )
    if (
        current["revision_id"] != payload.get("source_revision_id")
        or current["intent_sha256"] != payload.get("source_intent_sha256")
    ):
        raise Rejected("application_flow_source_revision_superseded", 423)
    selected = tranche(selected_tranche(actor, site))
    scope = {
        "tenant_id": actor.tenant, "site_id": identifier(site),
        "resource_id": actor.application, "environment": actor.environment,
    }
    result = request(
        "ASSURANCE", "POST",
        f"/v1/tenants/{actor.tenant}/migration-qualifications",
        {
            "scope": scope, "tranche_sha256": digest(selected),
            "release_sha256": selected["release_sha256"],
        },
        schema_name="migration-support-v1",
    )
    if (
        result["scope"] != scope
        or result["tranche_sha256"] != digest(selected)
        or result["release_sha256"] != selected["release_sha256"]
    ):
        raise Rejected("application_flow_qualification_scope_changed", 423)
    receipt = result["flow_evidence"]
    source_platform = binding.get("source", {}).get("platform")
    target_platform = binding.get("target", {}).get("platform")
    if (
        source_platform not in {"openstack", "vmware", "ahv"}
        or target_platform != payload.get("destination_platform")
    ):
        raise Rejected("application_flow_migration_platform_mismatch", 423)
    if not isinstance(receipt, dict) or any(
        receipt.get(field) != expected
        for field, expected in (
            ("assessment_id", payload.get("assessment_id")),
            ("source_revision_id", payload.get("source_revision_id")),
            ("source_intent_sha256", payload.get("source_intent_sha256")),
            ("context_sha256", saved["context_sha256"]),
            ("selections_sha256", digest(payload["selections"])),
            ("native_controls_sha256", payload.get("native_controls_sha256")),
            ("omissions_sha256", digest(payload.get("omissions", []))),
            ("destination_generation_id", payload.get("destination_generation_id")),
            ("platform", target_platform),
            ("source_platform", source_platform),
            ("source_profile_sha256", binding["source"]["profile_sha256"]),
            ("target_profile_sha256", binding["target"]["profile_sha256"]),
            ("migration_method", binding["method"]),
            ("level", "E4"),
            ("decision", "accepted"),
            ("native_write_authorized", False),
        )
    ):
        raise Rejected("independent_application_flow_e4_required", 423)
    # Vendor-neutral E4 effective-security proof is checked again at native
    # admission. A collected group expression or firewall-rule ID alone
    # cannot make an NSX or Prism mapping eligible.
    security_cases = receipt.get("security_cases")
    selected_bindings = payload["selections"]
    platform = payload.get("destination_platform")
    if not isinstance(security_cases, list) or len(security_cases) > 512:
        raise Rejected("native_security_e4_cases_missing", 423)
    if platform in {"vmware", "ahv", "openstack"}:
        from planning.domain.effective_security import qualify as qualify_effective_security
        from planning.domain.security_boundary import compare as compare_policy_boundary

        selected = {row["source_flow_id"]: row for row in selected_bindings}
        if len(selected) != len(selected_bindings):
            raise Rejected("native_security_flow_selection_ambiguous", 423)
        checked: set[str] = set()
        for case in security_cases:
            if not isinstance(case, dict) or set(case) != {
                "source_flow_id", "flow", "source_document", "document", "boundary"
            }:
                raise Rejected("native_security_e4_case_invalid", 423)
            flow_id = case["source_flow_id"]
            source = case["flow"]
            if (
                flow_id not in selected or flow_id in checked
                or not isinstance(source, dict)
                or set(source) != {"from", "to", "protocol", "port"}
                or digest(source) != flow_id
                or not isinstance(case["document"], dict)
                or case["document"].get("platform") != platform
                or not isinstance(case["source_document"], dict)
                or case["source_document"].get("platform") != source_platform
                or case["source_document"].get("api_profile", {}).get("profile_sha256")
                    != binding["source"]["profile_sha256"]
                or case["document"].get("api_profile", {}).get("profile_sha256")
                    != binding["target"]["profile_sha256"]
            ):
                raise Rejected("native_security_e4_case_mismatch", 423)
            boundary = compare_policy_boundary(
                case["source_document"], case["document"], case["boundary"], now,
            )
            if boundary["status"] != "qualified":
                raise Rejected("native_security_policy_boundary_unqualified", 423)
            source_result = qualify_effective_security(
                case["source_document"], source, now,
            )
            if source_result["status"] != "qualified":
                raise Rejected("native_source_security_e4_unqualified", 423)
            result = qualify_effective_security(case["document"], source, now)
            if (
                result["status"] != "qualified"
                or result["effective_rule_native_ref"]
                    != selected[flow_id]["rule_native_ref"]
                or "path:" + result["path_sha256"]
                    != selected[flow_id]["route_native_ref"]
            ):
                raise Rejected("native_security_e4_effective_behavior_unqualified", 423)
            checked.add(flow_id)
        if checked != set(selected):
            raise Rejected("native_security_e4_flow_coverage_incomplete", 423)
    else:
        raise Rejected("unsupported_native_security_platform", 423)
    omissions = payload.get("omissions", [])
    if omissions and (
        receipt["omissions_approved"] is not True
        or not isinstance(receipt["omission_approver_id"], str)
        or receipt["omission_approver_id"] == str(saved["reviewed_by_actor"])
    ):
        raise Rejected("independent_optional_flow_approval_required", 423)
    if (
        type(receipt["observed_at"]) is not int
        or not 0 <= now - receipt["observed_at"] <= 30
        or type(receipt["expires_at"]) is not int
        or not now < receipt["expires_at"] <= receipt["observed_at"] + 60
        or receipt["checks"] != {
            k: "passed" for k in (
                "native_controls", "source_completeness", "allowed_traffic",
                "denied_traffic", "return_path", "tenant_isolation",
                "application_validation",
            )
        }
    ):
        raise Rejected("independent_application_flow_evidence_expired", 423)
