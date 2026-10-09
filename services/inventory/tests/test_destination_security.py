"""API-observed network policies are selectable only when source-defined."""

import pytest

from inventory.domain.destination_security import (
    require_matching_openstack_rules,
    select_security_mappings,
    source_security_ids,
    source_rule_choices,
)
from inventory.domain.discovery import Rejected
from inventory.domain.migration import destination_input


def source(groups=("source-g",), *, port_security=True):
    return {
        "platform": "openstack",
        "schema_version": 3, "native_scope": "project-1",
        "guest_id": "otherLinux64Guest",
        "nics": [{"key": 0}],
        "native": {"metadata": {
            "ports": [{"id": "port-1", "project_id": "project-1",
                       "security_groups": list(groups),
                       "port_security_enabled": port_security}],
            "security_groups": [
                {"id": g, "project_id": "project-1",
                 "semantics_sha256": "a" * 64,
                 "rules": [{"id": "rule-" + g, "semantic_sha256": "f" * 64}]}
                for g in groups
            ],
        }},
    }


def destination(semantics="a" * 64):
    return {
        "platform": "openstack", "project_id": "project-2",
        "security_groups": [{"id": "target-g", "project_id": "project-2",
                             "semantics_sha256": semantics,
                             "rules": [{"id": "target-rule", "semantic_sha256": "f" * 64}]}],
    }


def review(items=None):
    return {
        "destination": {
            "platform": "openstack", "project_id": "project-2",
            "security_mappings": items if items is not None else [
                {"source_id": "source-g", "destination_id": "target-g"}
            ],
            "flow_mappings": [{"source_group_id": "source-g",
                               "source_rule_id": "rule-source-g",
                               "destination_rule_id": "target-rule"}],
        },
    }


def test_missing_source_policy_observation_is_unknown_not_empty():
    for bad in (
        {**source(), "platform": "ahv"},
        {**source(), "native": {"metadata": {}}},
        source(port_security=False),
        {**source(), "native": {"metadata": {"ports": [
            {"id": "port-1", "security_groups": ["source-g"]}
        ]}}},
    ):
        assert source_security_ids(bad) is None
        # Owner can save the rest of the review, but confirmation is held.
        destination_input({"destination": None}, bad, destination())
        with pytest.raises(Rejected, match="source_security_policy_observation_required"):
            destination_input(review(), bad, destination())


def test_exact_source_group_must_be_mapped_to_api_observed_target_group():
    valid = review()
    assert source_security_ids(source()) == ["source-g"]
    destination_input(valid, source(), destination())
    for invalid in (
        [],
        [{"source_id": "made-up", "destination_id": "target-g"}],
        [{"source_id": "source-g", "destination_id": "invented"}],
        [{"source_id": "source-g", "destination_id": "target-g"},
         {"source_id": "source-g", "destination_id": "target-g"}],
    ):
        with pytest.raises(Rejected):
            destination_input(review(invalid), source(), destination())


def test_only_matching_native_traffic_semantics_are_eligible_candidates():
    with pytest.raises(Rejected, match="destination_security_flow_equivalence_unproven"):
        destination_input(review(), source(), destination("b" * 64))
    with pytest.raises(Rejected, match="destination_security_flow_equivalence_unproven"):
        destination_input(review(), source(), destination(None))
    incomplete = source()
    incomplete["native"]["metadata"]["security_groups"] = []
    with pytest.raises(Rejected, match="destination_security_flow_equivalence_unproven"):
        destination_input(review(), incomplete, destination())


def test_absent_source_security_is_not_an_invitation_to_select_unneeded_rules():
    without = source(groups=())
    assert source_security_ids(without) == []
    destination_input({"destination": None}, without, destination())
    with pytest.raises(Rejected):
        destination_input(review(), without, destination())
    assert source_security_ids({"nics": [], "platform": "vmware"}) == []


def test_security_mapping_requires_one_to_one_existing_target_choices():
    ids = ["source-a", "source-b"]
    assert select_security_mappings(
        [{"source_id": "source-a", "destination_id": "dest-1"},
         {"source_id": "source-b", "destination_id": "dest-2"}],
        ids, {"dest-1", "dest-2"}
    ) == ["dest-1", "dest-2"]
    with pytest.raises(Rejected):
        select_security_mappings(
            [{"source_id": "source-a", "destination_id": "dest-1"},
             {"source_id": "source-b", "destination_id": "dest-1"}],
            ids, {"dest-1", "dest-2"}
        )


def test_every_observed_source_acl_rule_requires_existing_equivalent_target_id():
    assert source_rule_choices(source()) == [{
        "source_group_id": "source-g",
        "source_rule_id": "rule-source-g",
        "semantic_sha256": "f" * 64,
    }]
    for fault in ("missing", "invented", "changed_semantics", "duplicate"):
        body = review()
        target = destination()
        if fault == "missing":
            body["destination"]["flow_mappings"] = []
        elif fault == "invented":
            body["destination"]["flow_mappings"][0]["destination_rule_id"] = "new-rule"
        elif fault == "changed_semantics":
            target["security_groups"][0]["rules"][0]["semantic_sha256"] = "b" * 64
        else:
            body["destination"]["flow_mappings"] *= 2
        with pytest.raises(Rejected):
            destination_input(body, source(), target)


def test_missing_native_acl_details_preserve_empty_draft_but_not_invented_rule():
    incomplete = source()
    incomplete["native"]["metadata"]["security_groups"][0]["rules"] = None
    assert source_rule_choices(incomplete) is None
    # Profile is held by WorkloadProfiles._view. Unknown never means no traffic.
    draft = review()
    draft["destination"]["flow_mappings"] = []
    destination_input(draft, incomplete, destination())
    with pytest.raises(Rejected, match="source_security_rule_observation_required"):
        destination_input(review(), incomplete, destination())


def test_same_rule_id_on_wrong_destination_group_cannot_be_selected():
    target = destination()
    target["security_groups"][0]["rules"] = []
    target["security_groups"].append({
        "id": "unselected-group", "project_id": "project-2",
        "semantics_sha256": "a" * 64,
        "rules": [{"id": "target-rule", "semantic_sha256": "f" * 64}],
    })
    with pytest.raises(Rejected, match="destination_security_rule_choice_unproven"):
        destination_input(review(), source(), target)
