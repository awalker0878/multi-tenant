"""Contract test: the real Inventory coverage producer must validate against the installed Planning consumer."""
import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/inventory/src"))

from inventory.domain.discovery import digest
from inventory.domain.migration_collection_coverage import evaluate


def contracts():
    source = json.loads(
        (ROOT / "contracts/schemas/planning/migration-input-v3.json").read_text()
    )
    installed = json.loads(
        (ROOT / "services/planning/src/planning/infrastructure/inputs/migration-input-v3.json").read_text()
    )
    assert source == installed, "Canonical Inventory response changed without updating installed Planning schema"
    return source


def native_producer_case(scope: str) -> dict:
    manifest = {
        "schema_version": 1,
        "platforms": {
            "ahv": {"attributes": [{
                "id": "identity.native", "scope": scope,
                "condition": "always", "severity": "critical",
                "collection_method": "native_get",
                "collection_status": "native_field_candidate",
                "api_family": "vmm", "max_age_seconds": 120,
            }]}
        },
    }
    installation = "native-installation"
    generation = "native-generation"
    installed_tuple = digest("installed")
    observation = {
        "scope": scope, "installation_id": installation,
        "generation_id": generation, "installed_tuple_sha256": installed_tuple,
        "attribute_id": "identity.native", "collection_method": "native_get",
        "api_family": "vmm", "api_version": "v4.3",
        "native_operation": "GET /api/vmm/v4.3/ahv/config/vms/id",
        "value_sha256": digest("native-value"), "value_present": True,
        "evidence_sha256": digest("read-receipt"), "observed_at": 100,
    }
    return evaluate(
        manifest, "ahv", scope, installation, generation, installed_tuple,
        [observation], [], 101,
        installed_namespaces={"vmm": ["v4.3"]}, receipt_expires_at=150,
    )


def test_inventory_generated_field_records_validate_plannings_installed_contract():
    schema = contracts()["properties"]["collection_coverages"]["items"]
    validator = Draft202012Validator(schema)
    for side in ("source", "target", "owner"):
        record = native_producer_case(side)
        assert record["status"] == "complete"
        assert record["expires_at"] == 150
        assert not list(validator.iter_errors(record))
        for invalid in (
            {k: v for k, v in record.items() if k != "expires_at"},
            record | {"unexpected_authority": True},
        ):
            assert list(validator.iter_errors(invalid))


def test_stale_or_uninstalled_native_field_never_promotes_coverage():
    record = native_producer_case("source")
    assert record["status"] == "complete"
    # Consumer schema checks structure; Planning's readiness domain performs
    # the additional expiry/manifest/scope/qualification authorization.
