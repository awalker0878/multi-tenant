"""Cross-owner contracts for composed directions; synthetic data grants no authority."""

import copy
import itertools
import json
import sys
from pathlib import Path
from uuid import uuid4
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate_spec

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / p)
    for p in ("services/planning/src", "services/lifecycle/src", "workers/lifecycle/src")
]
from planning.domain.migration_outcomes import validate_outcomes as planning_validate
from lifecycle.domain.migration_outcomes import (
    validate_outcomes as lifecycle_validate,
    requirements,
)
from planning.domain.model import digest
from planning.domain.model import Rejected as PlanningHeld
from lifecycle.domain.execution import Rejected as LifecycleHeld

for name in (
    "inventory-v1.9.json",
    "lifecycle-native-jobs-v1.1.json",
    "worker-migration-effect-v2.1.json",
    "worker-migration-method-v2.json",
    "planning-migration-v1.6.json",
):
    spec = json.loads((ROOT / "contracts/openapi" / name).read_text())
    validate_spec(spec)
    client = ROOT / "apps/console/resources/contracts" / name
    if client.exists():
        assert client.read_bytes() == (ROOT / "contracts/openapi" / name).read_bytes()
api = json.loads((ROOT / "contracts/openapi/inventory-v1.9.json").read_text())
fixture = json.loads((ROOT / "contracts/fixtures/inventory/vmware-destination-v1.json").read_text())
for name, value in [
    ("VmwareTargetCapabilityProfile", fixture["target"]),
    ("MigrationReviewInput", fixture["review"]),
]:
    Draft202012Validator(
        {"$ref": "#/components/schemas/" + name, "components": api["components"]},
        format_checker=FormatChecker(),
    ).validate(value)
owner = ROOT / "contracts/schemas/planning/migration-input-v3.json"
assert (
    owner.read_bytes()
    == (
        ROOT / "services/planning/src/planning/infrastructure/inputs/migration-input-v3.json"
    ).read_bytes()
)
validator = Draft202012Validator(
    json.loads((ROOT / "contracts/schemas/planning/migration-outcomes-v1.json").read_text()),
    format_checker=FormatChecker(),
)
dataset = str(uuid4())
bound = {"datasets": [dataset], "owner_inputs_sha256": digest("owner")}
artifacts = {"guest": digest("guest")}
for source, target in itertools.product(("vmware", "openstack", "ahv"), repeat=2):
    o = {
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
                "semantics_sha256": digest("semantics"),
            }
        ],
        "datasets": {dataset: digest("dataset-validation")},
    }
    validator.validate(o)
    for validate in (planning_validate, lifecycle_validate):
        validate(o, bound, artifacts)
    assert len(requirements(o)) == 15
    for missing in o["services"]:
        bad = copy.deepcopy(o)
        bad["services"].pop(missing)
        assert not validator.is_valid(bad)
        for validate in (planning_validate, lifecycle_validate):
            try:
                validate(bad, bound, artifacts)
            except (PlanningHeld, LifecycleHeld):
                pass
            else:
                raise AssertionError("partial service acceptance")
print(
    "All nine directions share complete outcome semantics; 144 partial-service owner validations denied. VMware mappings and new internal contracts validate."
)

# A method enum cannot silently fall back to a native VM disk adapter. Validate
# actual typed data-owner operations against both the worker and published wire
# contract, with native destination scopes rather than UUIDs for every platform.
from lifecycle_worker.application.native import NativeBinding, NativeHeld
from lifecycle_worker.infrastructure.migration_method import (
    MECHANISMS,
    OPERATIONS,
    contract,
    measured,
)

method_api = json.loads((ROOT / "contracts/openapi/worker-migration-method-v2.json").read_text())


def wire(schema, value):
    Draft202012Validator(
        {"$ref": "#/components/schemas/" + schema, "components": method_api["components"]},
        format_checker=FormatChecker(),
    ).validate(value)


count = 0
for source, target in itertools.product(("vmware", "openstack", "ahv"), repeat=2):
    for method, stage_ops in OPERATIONS.items():
        for stage, operation in stage_ops.items():
            datasets = {
                str(uuid4()): {
                    k: digest(k) for k in ("source_sha256", "target_sha256", "consistency_sha256")
                }
            }
            c = {
                "method": method,
                "operation": operation,
                **{
                    side: {
                        "platform": platform,
                        "installation_id": str(uuid4()),
                        "native_identity_sha256": digest([side, platform]),
                    }
                    for side, platform in (("source", source), ("target", target))
                },
                "datasets": datasets,
                "mechanism": {
                    "kind": MECHANISMS[method],
                    "version": "synthetic-1",
                    "artifact_sha256": digest("artifact"),
                    "qualification_sha256": digest("qualification"),
                },
                **{
                    k: digest(k)
                    for k in (
                        "consistency_boundary_sha256",
                        "writer_fence_sha256",
                        "recovery_sha256",
                        "predecessor_receipt_sha256",
                    )
                },
                "reverse_qualification_sha256": digest("reverse")
                if stage == "reverse_sync"
                else None,
                "limits": {"max_seconds": 120, "max_lag_seconds": 0, "max_data_loss_bytes": 0},
            }
            p = {
                "schema_version": 2,
                "kind": "migration_owner_protocol",
                "stage": stage,
                "protocol_sha256": digest("protocol"),
                "parameters": {},
                "method_contract": c,
            }
            b = {
                **{
                    k: str(uuid4())
                    for k in (
                        "tenant_id",
                        "site_id",
                        "resource_id",
                        "job_id",
                        "operation_id",
                        "attempt_id",
                        "campaign_id",
                        "executor_id",
                        "epoch",
                        "custody_id",
                    )
                },
                "project_id": "datacenter-1"
                if target == "vmware"
                else uuid4().hex
                if target == "openstack"
                else str(uuid4()),
                "plan_digest": digest("plan"),
                "operation_plan_sha256": digest(p),
                "ownership_digest": digest("ownership"),
                "custody_generation": 1,
                "expires_at": 200,
            }
            NativeBinding.parse(b)
            assert contract(c, stage) == c
            wire("MethodEffectRequest", {"schema_version": 2, "binding": b, "intent": p})
            result = {
                "method_contract_sha256": digest(c),
                "source_writer_fenced": True,
                "target_writer_fenced": True,
                "elapsed_seconds": 10,
                "consistency_boundary_sha256": c["consistency_boundary_sha256"],
                "recovery_sha256": c["recovery_sha256"],
                "datasets": {
                    key: {
                        "dataset_sha256": digest(row),
                        "observed_at": 100,
                        "source_boundary_sha256": digest("source-boundary"),
                        "target_boundary_sha256": digest("target-boundary"),
                        "lag_seconds": 0,
                        "data_loss_bytes": 0,
                        "integrity_verified": True,
                        "metadata_verified": True,
                        "evidence_sha256": digest("observed"),
                    }
                    for key, row in datasets.items()
                },
            }
            wire("Measurement", result)
            assert measured(result, c, 100) == result
            invalid = copy.deepcopy(c)
            invalid["operation"] = "not_implemented"
            try:
                contract(invalid, stage)
            except NativeHeld:
                pass
            else:
                raise AssertionError("unknown data operation accepted")
            invalid = copy.deepcopy(result)
            invalid["datasets"] = {}
            try:
                measured(invalid, c, 100)
            except NativeHeld:
                pass
            else:
                raise AssertionError("missing dataset accepted")
            count += 1
print(
    f"{count} typed data-owner method operations and native destination scopes match worker contracts; no platform qualification granted."
)
