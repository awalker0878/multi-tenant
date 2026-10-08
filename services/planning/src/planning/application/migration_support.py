"""Directional eligibility from commissioned scope and authenticated Assurance reads."""

from collections.abc import Callable
from typing import Any

from planning.domain.expansion import matrix, tranche
from planning.domain.model import Actor, Rejected, digest

METHODS = {
    "VM_COLD_EXPORT": "cold_export",
    "VM_SNAPSHOT_BASELINE_APP_DELTA": "application_delta",
    "VM_SNAPSHOT_BASELINE_FILE_DELTA": "file_delta",
    "APPLICATION_REBUILD_RESTORE": "rebuild_restore",
    "EXTERNAL_BLOCK_REPLICATION": "block_replication",
}


class MigrationSupport:
    def __init__(
        self,
        scope: Callable[[Actor, str], dict[str, Any]],
        observations: Callable[[Actor, str, dict[str, Any]], list[dict[str, Any]]],
        clock: Callable[[], int],
    ) -> None:
        self.scope, self.observations, self.clock = scope, observations, clock

    def read(self, actor: Actor, site: str) -> dict[str, Any]:
        selected = tranche(self.scope(actor, site))
        records = self.observations(actor, site, selected)
        return {
            "schema_version": 1,
            "tranche_sha256": digest(selected),
            "release_sha256": selected["release_sha256"],
            "directions": matrix(selected, records, self.clock()),
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
        if len(candidates) != 1:
            raise Rejected("migration_direction_or_method_not_selected", 423)
        candidate = candidates[0]
        if candidate["source"]["installation_id"] == candidate["target"]["installation_id"]:
            raise Rejected("distinct_migration_environments_required", 423)
        records = self.observations(actor, site, selected)
        rows = matrix(selected, records, self.clock())
        qualified = [
            row
            for direction in rows
            for row in direction["routes"]
            if row["route_id"] == candidate["id"] and row["native_qualified"]
        ]
        if len(qualified) != 1:
            raise Rejected("migration_direction_qualification_required", 423)
