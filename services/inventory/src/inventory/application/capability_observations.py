"""Keep generation and ownership holds while adding independently measured observations."""

from typing import Any, Protocol

from inventory.application.discovery import Discovery
from inventory.application.planning import planning_input


class CapabilityObservations(Protocol):
    def read(self, base: dict[str, Any]) -> dict[str, Any] | None: ...


def capability_input(
    discovery: Discovery,
    tenant: str,
    site: str,
    endpoint: str,
    generation: str,
    observations: CapabilityObservations | None,
) -> dict[str, Any]:
    base = planning_input(discovery, tenant, site, endpoint, generation)
    observed = observations.read(base) if observations is not None else None
    base["capability_snapshot"] = None
    if observed is not None:
        inventory = observed.pop("inventory")
        for key in ("dimensions", "capabilities", "capacity", "domain_bindings", "workload_bindings"):
            base[key] = inventory[key]
        base["installed_provenance"] = "observed"
        base["expires_at"] = min(base["expires_at"], observed["expires_at"])
        base["capability_snapshot"] = observed
    return base
