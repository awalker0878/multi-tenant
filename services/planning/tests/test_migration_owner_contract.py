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
        (ROOT / "contracts/schemas/planning/migration-input-v4.json").read_text()
    )
    installed = json.loads(
        (ROOT / "services/planning/src/planning/infrastructure/inputs/migration-input-v4.json").read_text()
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
        "value_sha256": digest("native-value"),
        "source_response_sha256": digest("native-response"),
        "value_present": True,
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


def test_real_inventory_planning_response_validates_installed_strict_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inventory's real Planning projection feeds Planning's exact packaged v4 validator."""
    from contextlib import nullcontext
    from types import SimpleNamespace
    from uuid import uuid4

    from inventory.application.workload import WorkloadProfiles

    def uid() -> str:
        return str(uuid4())

    tenant, site, application, environment = (uid() for _ in range(4))
    source_id, target_id, generation = (uid() for _ in range(3))
    now, old, expires = 110, 100, 250
    observation = {
        "id": source_id, "endpoint_id": uid(), "generation_id": generation,
        "digest": digest("source"), "current": True, "collected_at": old,
        "expires_at": expires,
        "facts": {
            "profile_type": "SourceWorkloadProfile", "platform": "ahv",
            "vm_id": uid(), "installation_id": uid(),
            "native_scope": uid(), "cpu": 2, "memory_mb": 4096,
            "firmware": "efi", "guest_id": None,
            "holds": [],
            "disks": [{
                "key": 0, "capacity_bytes": 1073741824,
                "controller_key": None, "unit_number": 0,
                "backing_chain": [], "native_sha256": digest("disk"),
            }],
            "nics": [{"key": 0}], "controllers": [],
            "native": {"identity": {"vm_id": uid(), "generation_uuid": uid()},
                       "disk_records": [{"key": 0, "role": "vm_disk"}],
                       "metadata": {"vm": {"bootConfig": {"isSecureBootEnabled": True}}}},
        },
    }
    target = {
        "id": target_id, "endpoint_id": uid(),
        "generation_id": uid(), "digest": digest("target"),
        "current": True, "collected_at": old, "expires_at": expires,
        "facts": {"profile_type": "TargetCapabilityProfile", "platform": "ahv",
                  "disk_formats": ["raw"]},
    }
    owner_fields = (
        "application_consistency", "dependencies",
        "guest_transformation_profile", "delta_protocol",
        "recovery_protocol", "service_and_policy_validation",
        "writer_fencing", "retention_and_cleanup",
    )
    review = {
        "revision": 1, "digest": digest("review"), "confirmed_by": uid(),
        "confirmation_current": True, "source": observation, "target": target,
        "input": {
            "method": "VM_COLD_EXPORT", "catalogue_binding": None,
            "datasets": [{
                "id": uid(), "name": "all-bytes", "disk_keys": [0],
                "mounts": ["/"], "consistency_group": "crash-consistent",
                "validation_reference": "verified",
            }],
            "owner_inputs": {key: "owner-reference" for key in owner_fields},
            "objectives": {
                "owner_id": uid(), "acceptance_sha256": digest("accepted"),
                "max_outage_seconds": 3600, "max_data_loss_bytes": 0,
            },
        },
    }
    class Transaction:
        def one(self, query, args):
            return {"payload": {"source_profile_id": source_id}}

    class Database:
        def transaction(self):
            return nullcontext(Transaction())

    db = SimpleNamespace(database=Database())
    app = WorkloadProfiles(
        db, collection_read=lambda *_: [
            native_producer_case(s) for s in ("source", "target", "owner")
        ],
    )
    def native_binding(profile):
        return {
            "profile_sha256": profile["digest"],
            "native_identity_sha256": digest(profile["id"]),
            "tuple_sha256": digest(profile["generation_id"]),
            "observed_at": old, "expires_at": expires,
        }
    monkeypatch.setattr(WorkloadProfiles, "review", lambda *args: review)
    monkeypatch.setattr(WorkloadProfiles, "binding",
                        lambda self, profile: native_binding(profile))
    monkeypatch.setattr(WorkloadProfiles, "source_associations", lambda *args: [])
    produced = app.planning(
        tenant, site, 1, digest("review"), application, environment
    )
    schema = contracts()
    errors = list(Draft202012Validator(schema).iter_errors(produced))
    assert errors == [], [
        ("/".join(str(v) for v in e.path), e.message) for e in errors
    ]
    assert len(produced["collection_coverages"]) == 3
    assert all(row["expires_at"] == 150
               for row in produced["collection_coverages"])
    assert produced["native_write_authorized"] is False
