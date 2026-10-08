"""Contextual commissioning requirements; collection is never execution authority."""

from typing import Any

from inventory.domain.discovery import Rejected, shape
from inventory.domain.operator_inputs import FIELDS, GROUPS

OPERATIONS = [
    {"id": "discover", "label": "Discover an environment"},
    {"id": "provision", "label": "Provision an application"},
    {"id": "migrate", "label": "Migrate a workload"},
    {"id": "adopt", "label": "Adopt existing resources"},
    {"id": "operate", "label": "Accept a service into operation"},
    {"id": "retire", "label": "Retire managed resources"},
]
METHODS = [
    "APPLICATION_REBUILD_RESTORE",
    "VM_SNAPSHOT_BASELINE_APP_DELTA",
    "VM_SNAPSHOT_BASELINE_FILE_DELTA",
    "VM_COLD_EXPORT",
    "EXTERNAL_BLOCK_REPLICATION",
]


def validate_context(context: Any) -> None:
    shape(context, {"operation", "method"})
    if not isinstance(context["operation"], str) or context["operation"] not in {
        item["id"] for item in OPERATIONS
    }:
        raise Rejected("invalid_readiness_operation")
    if (context["operation"] == "migrate" and context["method"] not in METHODS) or (
        context["operation"] != "migrate" and context["method"] is not None
    ):
        raise Rejected("invalid_readiness_method")


def requirements(
    context: dict[str, Any] | None, source: str | None, target: str | None
) -> list[dict[str, Any]]:
    operation = context["operation"] if context else None
    method = context["method"] if context else None
    native = operation in {"provision", "migrate", "adopt", "retire"}
    active = operation in {"provision", "migrate", "adopt", "operate"}
    image = (
        operation == "migrate"
        and target in {"openstack", "ahv", "vmware"}
        and method
        in {"VM_COLD_EXPORT", "VM_SNAPSHOT_BASELINE_APP_DELTA", "VM_SNAPSHOT_BASELINE_FILE_DELTA"}
    )
    rules = {
        "source_writer_ref": operation == "migrate",
        "source_observer_ref": operation == "migrate"
        or (operation == "discover" and source is not None),
        "target_writer_ref": native,
        "target_observer_ref": native
        or operation == "operate"
        or (operation == "discover" and target is not None),
        "image_writer_ref": image,
        "image_observer_ref": image,
        "account_scope_ref": operation is not None,
        "trust_bundle_ref": operation is not None,
        "custody_ref": native or operation == "operate",
        "worker_fencing_ref": native or operation == "operate",
        "reservation_ref": operation in {"provision", "migrate", "adopt"},
        "guest_recipe_ref": operation in {"provision", "migrate"},
        "service_protocol_ref": active,
        "measurement_ref": operation in {"migrate", "operate"},
        "consistency_ref": operation in {"migrate", "adopt"},
        "delta_ref": operation == "migrate" and method != "VM_COLD_EXPORT",
        "writer_fencing_ref": operation in {"migrate", "adopt", "retire"},
        "traffic_ref": native,
        "restore_ref": active or operation == "retire",
        "recovery_ref": native or operation == "operate",
        "retention_ref": native or operation == "operate",
        "objectives_ref": active,
        "max_outage_seconds": active,
        "max_data_loss_bytes": active,
        "recovery_time_seconds": active,
        "max_active_migrations": operation in {"migrate", "operate"},
        "campaign_ref": native,
        "artifact_ref": native or operation == "operate",
        "security_ref": operation == "operate",
        "alert_ref": operation == "operate",
        "receiving_team_ref": operation == "operate",
        "support_ref": operation == "operate",
    }
    owners = {group["id"]: group["owner"] for group in GROUPS}
    label = next((item["label"] for item in OPERATIONS if item["id"] == operation), "Select a task")
    return [
        {
            **field,
            "required": rules[field["id"]],
            "applicability": (
                f"Required to {label.lower()}."
                if rules[field["id"]]
                else "Select a task and method to determine applicability."
                if context is None
                else "Not required for this task and method; any saved value is retained."
            ),
            "owner": owners[field["group"]],
            "example": str(max(field["minimum"], 1))
            if field["kind"] == "integer"
            else f"record:site-a/{field['id'].removesuffix('_ref')}",
            "format": "Whole number within the displayed bounds."
            if field["kind"] == "integer"
            else "Protected record identifier, 1–240 characters; no secret value or URL query.",
        }
        for field in FIELDS
    ]


def check_fields(
    fields: list[dict[str, Any]], values: dict[str, Any], evidence: dict[str, Any], stale: bool
) -> list[dict[str, Any]]:
    checks = []
    for field in fields:
        key = field["id"]
        proof = evidence.get(key, {})
        state = (
            "not_applicable"
            if not field["required"]
            else "missing"
            if key not in values
            else "stale"
            if stale
            else proof.get("state", "unverified")
        )
        actions = {
            "not_applicable": "No action is required for this task.",
            "missing": "Supply the approved value, then save this task's inputs.",
            "unverified": "Ask the owner to run the check and publish its bound evidence.",
            "stale": "Review changes or expired evidence and repeat the owner check.",
            "failed": "Resolve the owner's failed check and publish a new observation.",
            "verified": "Owner evidence is current; execution and qualification remain separate.",
            "unavailable": "Restore the evidence connection and check readiness again.",
        }
        checks.append(
            {
                "field_id": key,
                "state": state,
                "action": actions[state],
                "owner": field["owner"],
                "observed_at": proof.get("observed_at"),
                "expires_at": proof.get("expires_at"),
                "evidence_sha256": proof.get("evidence_sha256"),
            }
        )
    return checks
