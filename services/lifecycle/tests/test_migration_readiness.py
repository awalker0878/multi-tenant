"""Lifecycle consumes, but never trusts, Planning's route-readiness projection."""

from copy import deepcopy

import pytest

from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected
from lifecycle.domain.migration_readiness import verify


def specimen() -> tuple[dict, dict]:
    scope = {"tenant_id": "tenant", "resource_id": "app",
             "environment": "environment", "site_id": "site"}
    src, tgt, route = digest("source"), digest("target"), digest("route")
    content = {
        "scope": scope, "migration_campaign": {"route_sha256": route},
        "native_migration": {"migration": {
            "method": "VM_COLD_EXPORT",
            "source": {"profile_sha256": src},
            "target": {"profile_sha256": tgt},
            "outcomes": {"route_sha256": route},
        }},
    }
    data = {
        "schema_version": 1, "kind": "migration_route_readiness",
        "scope": {"tenant_id": "tenant", "application_id": "app",
                  "environment_id": "environment", "site_id": "site"},
        "route_sha256": route, "tranche_sha256": digest("tranche"),
        "release_sha256": digest("release"),
        "source": {"profile_sha256": src, "installation_id": "src",
                   "versions": {"vmm": "v4.2"}},
        "target": {"profile_sha256": tgt, "installation_id": "dst",
                   "versions": {"vmm": "v4.3"}},
        "method": "cold_export",
        "api_compatibility": {"operationally_eligible": True,
            "cases": [{"status": "eligible", "omission_accepted": False}]},
        "native_e3_qualified": True, "receiving_e4_accepted": True,
        "status": "eligible", "holds": [], "expires_at": 200,
        "evaluated_at": 100, "workload_admission_authorized": False,
        "native_write_authorized": False,
    }
    data["readiness_sha256"] = digest(data)
    return data, content


def test_lifecycle_checks_current_scope_and_integrity() -> None:
    value, content = specimen()
    verify(value, content, "tenant", 101)
    for edit in (
        lambda v: v.update(status="held"),
        lambda v: v.update(receiving_e4_accepted=False),
        lambda v: v["scope"].update(site_id="foreign"),
        lambda v: v.update(native_write_authorized=True),
    ):
        bad = deepcopy(value)
        edit(bad)
        with pytest.raises(Rejected):
            verify(bad, content, "tenant", 101)
    with pytest.raises(Rejected, match="migration_readiness_not_current"):
        verify(value, content, "tenant", 109)


def test_even_integrity_preserving_route_or_source_swap_is_held() -> None:
    value, content = specimen()
    for key, replacement in (("route_sha256", digest("other")),
                             ("source", {**value["source"], "profile_sha256": digest("alien")})):
        bad = deepcopy(value)
        bad[key] = replacement
        bad["readiness_sha256"] = digest({k: v for k, v in bad.items()
                                           if k != "readiness_sha256"})
        with pytest.raises(Rejected):
            verify(bad, content, "tenant", 101)
