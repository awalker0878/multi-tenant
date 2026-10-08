from copy import deepcopy

import pytest
from planning_fixture import ACTOR, NOW, REVISION, assessment, inputs, request, verify_fixture

from planning.domain.assessment import assess
from planning.domain.compilation import bind, compile_plan, diff, graph_order
from planning.domain.model import DIMENSIONS, PLATFORMS, Rejected, canonical, digest, profile


def test_two_destinations_explain_constraints() -> None:
    i, d, p, policy, q = inputs()
    good = assess(i, d, p, policy, q, "application.provision", "native_api", NOW)
    assert good["status"] == "eligible" and good["reserved"] is False
    d["capacity"]["vcpus"] = 3
    bad = assess(i, d, p, policy, q, "application.provision", "native_api", NOW)
    assert bad["status"] == "blocked"
    assert any(
        r["requirement"] == "capacity.vcpus" and r["reason"] == "observed_capacity_insufficient"
        for r in bad["findings"]
    )
    assert all(f["remediation"] and f["source"] for f in bad["findings"])


@pytest.mark.parametrize("dimension", DIMENSIONS)
def test_each_missing_dimension_holds(dimension: str) -> None:
    i, d, p, policy, q = inputs()
    del d["dimensions"][dimension]
    result = assess(i, d, p, policy, q, "application.provision", "native_api", NOW)
    assert not result["operationally_eligible"]
    assert any(
        f["requirement"] == dimension and f["reason"] == "dimension_not_observed"
        for f in result["findings"]
    )


@pytest.mark.parametrize("platform", PLATFORMS)
def test_all_platforms_retain_unknown_dimensions(platform: str) -> None:
    p = profile(platform, "1", {})
    assert len(p["dimensions"]) == 11
    assert all(row["declaration"]["status"] == "unknown" for row in p["dimensions"])


@pytest.mark.parametrize(
    "fault",
    [
        "expired",
        "revoked",
        "absent",
        "wrong_site",
        "wrong_artifact",
        "reverse",
        "E2",
        "partial",
        "old",
        "declared",
        "policy_expired",
    ],
)
def test_fail_closed_inputs(fault: str) -> None:
    i, d, p, policy, q = inputs()
    match fault:
        case "expired":
            q["expires_at"] = NOW
        case "revoked":
            q["revoked"] = True
        case "absent":
            q = {}
        case "wrong_site":
            q["scope"]["site_id"] = "other"
        case "wrong_artifact":
            q["scope"]["artifacts"] = dict(q["scope"]["artifacts"], adapter="b" * 64)
        case "reverse":
            q["scope"]["method"] = "reverse_route"
        case "E2":
            q["evidence_level"] = "E2"
        case "partial":
            d["completion"] = "partial"
        case "old":
            d["expires_at"] = NOW
        case "declared":
            d["installed_provenance"] = "declaration"
        case "policy_expired":
            policy["expires_at"] = NOW
    assert not assess(i, d, p, policy, q, "application.provision", "native_api", NOW)[
        "operationally_eligible"
    ]


@pytest.mark.parametrize(
    "key",
    [
        "placement.tenant_isolation",
        "placement.domain_isolation",
        "sovereignty.custody",
        "sovereignty.location",
        "sovereignty.data_path",
        "service.backup.owner",
    ],
)
def test_security_service_and_custody_never_default_allow(key: str) -> None:
    i, d, p, policy, q = inputs()
    del d["capabilities"][key]
    assert not assess(i, d, p, policy, q, "application.provision", "native_api", NOW)[
        "operationally_eligible"
    ]


def test_preference_retained_and_conditional_is_not_eligible() -> None:
    i, d, p, policy, q = inputs()
    i["requirements"] = [{"key": "unknown.preference", "value": True, "strength": "preferred"}]
    result = assess(i, d, p, policy, q, "application.provision", "native_api", NOW)
    assert result["operationally_eligible"]
    d["capabilities"]["guest.image"]["dependencies"] = ["image_owner_confirmation"]
    assert (
        assess(i, d, p, policy, q, "application.provision", "native_api", NOW)["status"]
        == "conditional"
    )


def test_semantic_content_determinism_and_approval_binding() -> None:
    a = assessment()
    content = compile_plan(a, 0, request())
    assert content["execution_ready"]
    assert digest(content) == digest(compile_plan(deepcopy(a), 0, request()))
    reordered = {k: content[k] for k in reversed(content)}
    assert digest(content) == digest(reordered)
    binding = bind(content, REVISION, ACTOR)
    changed = deepcopy(content)
    changed["effects"][0]["scope"]["native_scope"] = "different-project"
    assert bind(changed, REVISION, ACTOR)["digest"] != binding["digest"]
    assert diff(content, changed)
    assert content["native_write_authorized"] is False


@pytest.mark.parametrize("field", ["intent", "inventory", "profile", "policy", "qualification"])
def test_changed_pinned_input_changes_digest(field: str) -> None:
    a = assessment()
    old = compile_plan(a, 0, request())
    a["results"][0]["input_digests"][field] = "c" * 64
    assert digest(old) != digest(compile_plan(a, 0, request()))


def test_cyclic_missing_or_duplicate_effects_rejected() -> None:
    for effects in (
        [{"id": "a", "after": ["a"]}],
        [{"id": "a", "after": ["x"]}],
        [{"id": "a", "after": []}, {"id": "a", "after": []}],
    ):
        with pytest.raises(Rejected):
            graph_order(effects)


def test_ownership_collision_and_missing_state_hold() -> None:
    a = assessment()
    a["inputs"][0]["policy"]["ownership"] *= 2
    with pytest.raises(Rejected, match="overlapping"):
        compile_plan(a, 0, request())
    a = assessment()
    a["inputs"][0]["policy"]["native_api"] = None
    c = compile_plan(a, 0, request())
    assert not c["execution_ready"] and c["holds"] == ["reviewed_native_operation_plan_missing"]


@pytest.mark.parametrize("value", [1.5, float("nan"), {"secret": "no"}, 2**53, {"x": "\ud800"}])
def test_noncanonical_and_secrets_rejected(value: object) -> None:
    with pytest.raises(Rejected):
        canonical(value)


@pytest.mark.parametrize(
    "side,status",
    [("observation", "unknown"), ("qualification", "unknown"), ("qualification", "expired")],
)
def test_per_requirement_unknown_and_expired_support_cannot_pass(side: str, status: str) -> None:
    i, d, p, policy, q = inputs()
    capability = (d if side == "observation" else q)["capabilities"]["placement.tenant_isolation"]
    if status == "expired":
        capability["expires_at"] = NOW
    else:
        capability["status"] = status
    assert not assess(i, d, p, policy, q, "application.provision", "native_api", NOW)[
        "operationally_eligible"
    ]


def test_boolean_is_not_numeric_requirement_value() -> None:
    i, d, p, policy, q = inputs()
    d["capabilities"]["placement.tenant_isolation"]["values"] = [1]
    assert not assess(i, d, p, policy, q, "application.provision", "native_api", NOW)[
        "operationally_eligible"
    ]


@pytest.mark.parametrize("side", ["destination", "qualification"])
def test_plan_freshness_cannot_outlive_required_capability(side: str) -> None:
    assessed = assessment()
    row = assessed["inputs"][0]
    row[side]["capabilities"]["placement.tenant_isolation"]["expires_at"] = NOW + 10
    verify_fixture(row["qualification"])
    assessed["results"] = [
        assess(
            assessed["intent"]["intent"],
            row["destination"],
            row["profile"],
            row["policy"],
            row["qualification"],
            "application.provision",
            "native_api",
            NOW,
        )
    ]
    assert assessed["results"][0]["operationally_eligible"]
    assert compile_plan(assessed, 0, request())["input_fresh_until"] == NOW + 10


def test_optional_capability_does_not_shorten_required_freshness() -> None:
    i, d, p, policy, q = inputs()
    i["requirements"].append({"key": "optional.capability", "value": True, "strength": "preferred"})
    d["capabilities"]["optional.capability"] = {
        "status": "observed",
        "values": [True],
        "expires_at": NOW + 10,
        "dependencies": [],
    }
    q["capabilities"]["optional.capability"] = {
        **d["capabilities"]["optional.capability"],
        "status": "supported",
    }
    verify_fixture(q)
    result = assess(i, d, p, policy, q, "application.provision", "native_api", NOW)
    assert result["operationally_eligible"]
    assert result["expires_at"] == NOW + 1800


@pytest.mark.parametrize(
    "fault,reason",
    [
        ("unknown", "requirement_evidence_unassessed"),
        ("unsupported", "requirement_unsupported"),
        ("stale", "requirement_observation_expired"),
        ("mismatch", "constraint_not_satisfied"),
        ("dependency", "dependency_requires_confirmation"),
    ],
)
def test_lab_qualification_waiver_cannot_mask_observation_safety(fault: str, reason: str) -> None:
    i, d, p, policy, _ = inputs()
    observation = d["capabilities"]["placement.tenant_isolation"]
    if fault in {"unknown", "unsupported"}:
        observation["status"] = fault
    elif fault == "stale":
        observation["expires_at"] = NOW
    elif fault == "mismatch":
        observation["values"] = [False]
    else:
        observation["dependencies"] = ["independent-isolation-confirmation"]
    result = assess(i, d, p, policy, {}, "application.provision", "native_api", NOW)
    assert not result["operationally_eligible"]
    assert any(
        f["requirement"] == "placement.tenant_isolation" and f["reason"] == reason
        for f in result["findings"]
    )
