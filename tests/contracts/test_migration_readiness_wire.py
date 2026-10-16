"""End-to-end Planning producer and Lifecycle installed schema consumer E2 test.

All cross-context imports live in this shared contract test boundary, never
inside a single service's unit-test directory.
"""
from copy import deepcopy

import pytest

from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected
from lifecycle.infrastructure.migration_readiness_contract import verify
from planning.domain.migration_readiness import resolve_workload
from planning.infrastructure.migration_readiness_contract import validate_workload_contract

# This synthetic scope fixture is shared by the existing Lifecycle contract
# tests; it does not represent real provider qualification or a historical API.
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location

def specimen():
    path = Path(__file__).resolve().parents[2] / "services/lifecycle/tests/test_migration_readiness.py"
    locator = spec_from_file_location("_lifecycle_readiness_specimen", path)
    if locator is None or locator.loader is None:
        raise RuntimeError("Lifecycle readiness fixture missing")
    module = module_from_spec(locator)
    locator.loader.exec_module(module)
    return module.specimen()


def test_planning_producer_to_lifecycle_installed_readiness_contract() -> None:
    """Exercise the current producer, installed Planning schema and Lifecycle consumer.

    These are synthetic E2 inputs. They do not claim real provider E3/E4 custody.
    A static sample or mere matching schema files is insufficient for evidence.
    """
    expected, content = specimen()
    route = deepcopy(expected)
    route.pop("readiness_sha256")
    reconciliation = route.pop("workload_reconciliation")
    coverages = route.pop("collection_coverages")
    manifest = {
        "release_sha256": route["release_sha256"],
        "manifest_sha256": digest("manifest"),
        "platforms": {
            "vmware": {"source": ["identity"], "owner": ["identity"]},
            "ahv": {"target": ["identity"]},
        },
    }
    produced = resolve_workload(route, reconciliation, coverages, 100, manifest)
    assert produced == expected
    validate_workload_contract(produced)
    tenant = expected["scope"]["tenant_id"]
    verify(produced, content, tenant, 101)

    # Valid JSON with the wrong tenant and stale nested provenance still fails.
    with pytest.raises(Rejected):
        verify(produced, content, "10000000-0000-4000-8000-000000000002", 101)
    stale = deepcopy(coverages)
    stale[0]["expires_at"] = 101
    stale[0]["coverage_sha256"] = digest({
        key: value for key, value in stale[0].items()
        if key != "coverage_sha256"
    })
    held = resolve_workload(route, reconciliation, stale, 101, manifest)
    assert held["status"] == "held"
    with pytest.raises(Rejected):
        verify(held, content, tenant, 101)
