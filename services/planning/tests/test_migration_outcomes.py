"""Every direction composes explicit outcomes; partial receipts cannot qualify routes."""

from copy import deepcopy
from typing import Any

import pytest
from test_migration_plans import values

from planning.domain.migration_plan import compose_migration
from planning.domain.model import Rejected, digest


def outcomes(
    bound: dict[str, Any], artifacts: dict[str, Any], source: str, target: str
) -> dict[str, Any]:
    return {
        "source_platform": source,
        "target_platform": target,
        "owner_inputs_sha256": bound["owner_inputs_sha256"],
        "route_sha256": digest([source, target]),
        "guest_profile_sha256": artifacts["guest"],
        "guest": {k: digest(k) for k in ("boot", "drivers", "storage", "network", "identity")},
        "services": {
            k: digest(k)
            for k in ("ipam", "dns", "identity", "time", "trust", "logging", "monitoring", "backup")
        },
        "security": [
            {
                "id": "application",
                "source_rule_sha256": digest("source-rule"),
                "target_rule_sha256": digest("target-rule"),
                "semantics_sha256": digest("allowed-intent"),
            }
        ],
        "datasets": {key: digest(key) for key in bound["datasets"]},
    }


@pytest.mark.parametrize("source", ["vmware", "openstack", "ahv"])
@pytest.mark.parametrize("target", ["vmware", "openstack", "ahv"])
def test_each_direction_retains_all_outcome_requirements(source: str, target: str) -> None:
    base, bound, recipe = values()
    recipe.update(schema_version=3, outcomes=outcomes(bound, recipe["artifacts"], source, target))
    recipe["campaign"]["route_sha256"] = recipe["outcomes"]["route_sha256"]
    result = compose_migration(base, bound, recipe, 1000)
    migration = result["native_migration"]["migration"]
    assert migration["schema_version"] == 4
    assert migration["outcomes"] == recipe["outcomes"]
    assert migration["outcomes"]["source_platform"] == source
    assert migration["outcomes"]["target_platform"] == target
    assert result["native_migration"]["recipe_sha256"] == digest(recipe)


@pytest.mark.parametrize("fault", ["guest", "service", "rules", "duplicates", "datasets", "inputs"])
def test_recipe_rejects_incomplete_or_drifted_acceptance(fault: str) -> None:
    base, bound, recipe = values()
    o = outcomes(bound, recipe["artifacts"], "ahv", "vmware")
    recipe.update(schema_version=3, outcomes=o)
    if fault == "guest":
        o["guest_profile_sha256"] = digest("wrong")
    if fault == "service":
        o["services"].pop("backup")
    if fault == "rules":
        o["security"] = []
    if fault == "duplicates":
        o["security"].append(deepcopy(o["security"][0]))
    if fault == "datasets":
        o["datasets"] = {}
    if fault == "inputs":
        o["owner_inputs_sha256"] = digest("other-review")
    with pytest.raises(Rejected):
        compose_migration(base, bound, recipe, 1000)


@pytest.mark.parametrize("fault", ["campaign", "destination"])
def test_recipe_cannot_change_qualified_route_or_destination_platform(fault: str) -> None:
    base, bound, recipe = values()
    o = outcomes(bound, recipe["artifacts"], "openstack", "vmware")
    recipe.update(schema_version=3, outcomes=o)
    recipe["campaign"]["route_sha256"] = o["route_sha256"]
    if fault == "campaign":
        recipe["campaign"]["route_sha256"] = digest("another-route")
    else:
        bound["destination_sha256"] = digest("mapping")
        recipe["destination_sha256"] = bound["destination_sha256"]
        base["native_api"]["operation_plan"] = {
            "kind": "ahv_destination",
            "destination_sha256": bound["destination_sha256"],
        }
        recipe["base_content_sha256"] = digest(base)
        recipe["intents"]["import_target"] = digest(base["native_api"]["operation_plan"])
    with pytest.raises(Rejected, match="campaign_route_changed|destination_platform_changed"):
        compose_migration(base, bound, recipe, 1000)
