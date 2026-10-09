"""Service-only admission never trusts a Console-stored flow approval as proof."""
from copy import deepcopy
from uuid import uuid4

import pytest

from planning.domain.model import Actor, Rejected, digest
from planning.infrastructure import migration_support


def actor():
    return Actor(str(uuid4()), str(uuid4()), "plan.read",
                 str(uuid4()), str(uuid4()))


def test_independent_qualification_must_bind_current_source_and_exact_controls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_actor = actor()
    site = str(uuid4())
    source_revision, assessment, generation = [str(uuid4()) for _ in range(3)]
    saved = {
        "reviewed_by_actor": str(uuid4()),
        "context_sha256": "a" * 64,
        "payload": {
            "assessment_id": assessment,
            "source_revision_id": source_revision,
            "source_intent_sha256": "b" * 64,
            "destination_generation_id": generation,
            "destination_platform": "openstack",
            "native_controls_sha256": "c" * 64,
            "omissions": [],
            "selections": [{
                "source_flow_id": "d" * 64,
                "rule_native_ref": "neutron-rule-1",
                "route_native_ref": "neutron-route-1",
            }],
        },
    }
    now = 1000
    binding = {
        "source": {"platform": "vmware", "profile_sha256": "1" * 64},
        "target": {"platform": "openstack", "profile_sha256": "2" * 64},
        "method": "cold_export",
    }
    scope = {
        "tenant_id": current_actor.tenant, "site_id": site,
        "resource_id": current_actor.application,
        "environment": current_actor.environment,
    }
    proof = {
        "schema_version": 1, "assessment_id": assessment,
        "source_revision_id": source_revision,
        "source_intent_sha256": "b" * 64,
        "context_sha256": "a" * 64,
        "selections_sha256": digest(saved["payload"]["selections"]),
        "native_controls_sha256": "c" * 64,
        "destination_generation_id": generation,
        "omissions_sha256": digest([]),
        "omissions_approved": False, "omission_approver_id": None,
        "platform": "openstack", "source_platform": "vmware",
        "source_profile_sha256": "1" * 64,
        "target_profile_sha256": "2" * 64,
        "migration_method": "cold_export",
        "security_cases": [],
        "level": "E4",
        "decision": "accepted", "native_write_authorized": False,
        "observed_at": now, "expires_at": now + 30,
        "checks": {
            k: "passed" for k in (
                "native_controls", "source_completeness", "allowed_traffic",
                "denied_traffic", "return_path", "tenant_isolation",
                "application_validation",
            )
        },
    }
    selected = {"release_sha256": "e" * 64}
    monkeypatch.setattr(migration_support, "selected_tranche", lambda a, s: selected)
    import planning.domain.expansion as expansion
    monkeypatch.setattr(expansion, "tranche", lambda d: d)
    response = {
        "scope": scope, "tranche_sha256": digest(selected),
        "release_sha256": selected["release_sha256"],
        "flow_evidence": proof, "records": [],
    }
    def request(owner, method, path, *args, **kwargs):
        if owner == "CATALOGUE":
            return {"revision_id": source_revision, "intent_sha256": "b" * 64}
        if owner == "ASSURANCE":
            return response
        raise AssertionError(owner)
    monkeypatch.setattr(migration_support, "request", request)

    migration_support.current_application_flow_proof(current_actor, site, saved, now, binding)
    for field, value in (
        ("selections_sha256", "9" * 64),
        ("native_controls_sha256", "9" * 64),
        ("context_sha256", "9" * 64),
        ("observed_at", now - 31),
        ("expires_at", now),
    ):
        changed = deepcopy(response)
        changed["flow_evidence"] = {**proof, field: value}
        monkeypatch.setattr(migration_support, "request",
            lambda owner, method, path, *args, **kwargs:
            changed if owner == "ASSURANCE" else
            {"revision_id": source_revision, "intent_sha256": "b" * 64})
        with pytest.raises(Rejected):
            migration_support.current_application_flow_proof(current_actor, site, saved, now, binding)

    # An owner can request an optional omission, but their own signature
    # cannot double as the independent receiving approval.
    omission = [{"source_flow_id": "f" * 64,
                 "reason_code": "replaced_by_native_service"}]
    saved["payload"]["omissions"] = omission
    proof["omissions_sha256"] = digest(omission)
    proof["omissions_approved"] = True
    proof["omission_approver_id"] = saved["reviewed_by_actor"]
    monkeypatch.setattr(migration_support, "request", request)
    with pytest.raises(Rejected, match="independent_optional_flow_approval_required"):
        migration_support.current_application_flow_proof(current_actor, site, saved, now, binding)
    proof["omission_approver_id"] = str(uuid4())
    migration_support.current_application_flow_proof(current_actor, site, saved, now, binding)


def test_unavailable_or_superseded_source_requires_new_assessment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    a = actor()
    monkeypatch.setattr(migration_support, "request",
        lambda *args, **kwargs: {
            "revision_id": str(uuid4()), "intent_sha256": "b" * 64,
        })
    with pytest.raises(Rejected, match="source_revision_superseded"):
        migration_support.current_application_flow_proof(a, str(uuid4()), {
            "payload": {"source_revision_id": str(uuid4()),
                        "source_intent_sha256": "b" * 64},
        }, 1000, {"source": {"platform": "vmware", "profile_sha256": "1" * 64},
                    "target": {"platform": "openstack", "profile_sha256": "2" * 64},
                    "method": "cold_export"})
