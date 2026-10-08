"""Directional eligibility from commissioned scope and authenticated Assurance reads."""

from collections.abc import Callable
from typing import Any

from planning.domain.api_compatibility import evaluate as evaluate_api
from planning.domain.capability_definitions import METHOD_ALIASES as METHODS
from planning.domain.expansion import matrix, tranche
from planning.domain.model import Actor, Rejected, digest


class MigrationSupport:
    def __init__(
        self,
        scope: Callable[[Actor, str], dict[str, Any]],
        observations: Callable[[Actor, str, dict[str, Any]], list[dict[str, Any]]],
        clock: Callable[[], int],
        api_observations: Callable[[Actor, str, dict[str, Any]], dict[str, Any] | None]
        | None = None,
    ) -> None:
        self.scope, self.observations, self.clock = scope, observations, clock
        self.api_observations = api_observations

    def api_status(
        self, actor: Actor, site: str, selected: dict[str, Any]
    ) -> dict[str, Any]:
        if "api_usage" not in selected:
            return {
                "status": "unknown",
                "operationally_eligible": False,
                "cases": [],
                "administrator_alerts": [],
                "native_write_authorized": False,
            }
        evidence = (
            self.api_observations(actor, site, selected)
            if self.api_observations is not None
            else None
        )
        return evaluate_api(
            selected, evidence, self.clock(),
            tenant_id=actor.tenant, application_id=actor.application,
            environment_id=actor.environment,
        )

    def read(self, actor: Actor, site: str) -> dict[str, Any]:
        selected = tranche(self.scope(actor, site))
        records = self.observations(actor, site, selected)
        directions = matrix(selected, records, self.clock())
        by_id = {route["id"]: route for route in selected["routes"]}
        for direction in directions:
            for row in direction["routes"]:
                route = by_id[row["route_id"]]
                if "api_usage" not in route:
                    continue
                api = self.api_status(actor, site, route)
                row["api_compatibility"] = api
                if not api["operationally_eligible"]:
                    row["blockers"].append("api_capabilities_unresolved")
                    row["native_qualified"] = False
                    row["operationally_accepted"] = False
        return {
            "schema_version": 1,
            "tranche_sha256": digest(selected),
            "release_sha256": selected["release_sha256"],
            "directions": directions,
            "native_write_authorized": False,
        }

    def require(self, actor: Actor, site: str, binding: dict[str, Any]) -> None:
        selected = tranche(self.scope(actor, site))
        candidates = [
            row
            for row in selected["routes"]
            if row["source"]["profile_sha256"] == binding["source"]["profile_sha256"]
            and row["target"]["profile_sha256"] == binding["target"]["profile_sha256"]
            and row["method"] == METHODS.get(binding["method"])
        ]
        if "artifacts" in binding:
            outcomes = binding.get("outcomes")
            if not isinstance(outcomes, dict):
                raise Rejected("migration_complete_outcomes_required", 423)
            candidates = [r for r in candidates if digest(r) == outcomes.get("route_sha256")]
        if not candidates:
            raise Rejected("migration_direction_or_method_not_selected", 423)
        if any(
            r["source"]["installation_id"] == r["target"]["installation_id"] for r in candidates
        ):
            raise Rejected("distinct_migration_environments_required", 423)
        if "artifacts" in binding:
            # The authenticated Inventory review selects platform profiles and a method;
            # the commissioned recipe then selects one exact guest/artifact variant.
            # Several independently qualified variants can share the same profiles.
            if len(candidates) != 1:
                raise Rejected("migration_direction_or_method_not_selected", 423)
            outcomes = binding["outcomes"]
            if not isinstance(outcomes, dict):
                raise Rejected("migration_complete_outcomes_required", 423)
            candidate = candidates[0]
            constraints = candidate["constraints"]
            if "maximum_data_loss_bytes" in constraints:
                if (
                    constraints["maximum_data_loss_bytes"]
                    > binding["objectives"]["max_data_loss_bytes"]
                ):
                    raise Rejected("migration_data_loss_objective_unqualified", 423)
            elif constraints["maximum_data_loss_seconds"] != 0:
                # Seconds cannot establish a byte allowance without a qualified bound.
                raise Rejected("migration_data_loss_units_unqualified", 423)
            if (
                outcomes["route_sha256"] != digest(candidate)
                or outcomes["source_platform"] != candidate["source"]["platform"]
                or outcomes["target_platform"] != candidate["target"]["platform"]
                or binding["artifacts"]["guest"] != candidate["guest_profile_sha256"]
                or digest(outcomes["guest"]) != candidate.get("guest_outcomes_sha256")
                or digest(binding["artifacts"]) != candidate["artifacts_sha256"]
                or digest(outcomes["services"]) != candidate["services_sha256"]
                or digest(outcomes["security"]) != candidate["policy_sha256"]
                or digest(outcomes["datasets"]) != candidate["data_sha256"]
                or binding["artifacts"]["recovery"] != candidate["recovery_sha256"]
                or {d["format"] for d in binding["disks"]}
                != {candidate["constraints"]["disk_format"]}
                or candidate["constraints"]["maximum_outage_seconds"]
                > binding["objectives"]["max_outage_seconds"]
            ):
                raise Rejected("migration_qualified_artifacts_or_requirements_changed", 423)
        for candidate in candidates:
            if "api_usage" in candidate and not self.api_status(
                actor, site, candidate
            )["operationally_eligible"]:
                raise Rejected("migration_api_capabilities_unresolved", 423)
        records = self.observations(actor, site, selected)
        rows = matrix(selected, records, self.clock())
        qualified = [
            row
            for direction in rows
            for row in direction["routes"]
            if row["route_id"] in {candidate["id"] for candidate in candidates}
            and row["native_qualified"]
        ]
        if not qualified:
            raise Rejected("migration_direction_qualification_required", 423)
