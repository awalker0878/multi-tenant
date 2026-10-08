"""Owner-supplied commissioning references; never credentials or native authority."""

import re
from typing import Any

from inventory.domain.discovery import Rejected, shape

GROUPS = [
    {
        "id": "access",
        "label": "Accounts and trust",
        "owner": "Platform and identity owners",
        "scope": "P07 / P08",
    },
    {
        "id": "control",
        "label": "Execution and independent verification",
        "owner": "Platform and security owners",
        "scope": "P07 / P08",
    },
    {
        "id": "recovery",
        "label": "Application recovery and cutover",
        "owner": "Application and service owners",
        "scope": "P07 / P08",
    },
    {
        "id": "targets",
        "label": "Operating targets",
        "owner": "Application and operations owners",
        "scope": "P08 / P10",
    },
    {
        "id": "receiving",
        "label": "Qualification and service handover",
        "owner": "Qualification and receiving teams",
        "scope": "P10",
    },
]
FIELDS: list[dict[str, Any]] = []


def reference(group: str, id_: str, label: str, help_: str) -> None:
    FIELDS.append(
        {
            "id": id_,
            "group": group,
            "label": label,
            "help": help_,
            "kind": "reference",
            "minimum": None,
            "maximum": None,
        }
    )


for side, label in (
    ("source", "Source platform"),
    ("target", "Destination platform"),
    ("image", "Image transfer"),
):
    reference(
        "access",
        side + "_writer_ref",
        label + " execution account reference",
        "Protected secret-store record for the scoped execution identity. Supply its record "
        "identifier, never its secret value.",
    )
    reference(
        "access",
        side + "_observer_ref",
        label + " verification account reference",
        "Separate read-only identity used to verify effects independently of the execution "
        "account.",
    )
for group, id_, label, help_ in (
    (
        "access",
        "account_scope_ref",
        "Account permissions and scope record",
        "Approved projects, datacentres, resource scope, expiry and permissions for all six "
        "accounts.",
    ),
    (
        "access",
        "trust_bundle_ref",
        "TLS trust and rotation record",
        "Approved certificate authorities, endpoint identity checks, secret rotation and "
        "revocation procedure.",
    ),
    (
        "control",
        "custody_ref",
        "Independent recovery custody record",
        "Owner and protected provider state used to reconcile effects after a worker or "
        "journal restore.",
    ),
    (
        "control",
        "worker_fencing_ref",
        "Stale worker exclusion procedure",
        "How the platform prevents a revoked or restored worker from issuing further native "
        "changes.",
    ),
    (
        "control",
        "reservation_ref",
        "Capacity and address reservation procedure",
        "Reserve, confirm, reconcile and release capacity, IP addresses and service allocations.",
    ),
    (
        "control",
        "guest_recipe_ref",
        "Guest preparation recipe",
        "Reviewed image, driver and hardening recipe, including the tested converter image "
        "when applicable.",
    ),
    (
        "control",
        "service_protocol_ref",
        "Shared service integration procedures",
        "Owner protocols for DNS, IPAM, identity, time, trust, logging, monitoring and backup.",
    ),
    (
        "control",
        "measurement_ref",
        "Transfer and concurrency measurement record",
        "Measured route throughput, API limits, phase concurrency and current resource "
        "capacity. Supply the retained observation reference.",
    ),
    (
        "recovery",
        "consistency_ref",
        "Application consistency procedure",
        "Application owner procedure for quiescing writes and establishing a consistent "
        "migration baseline.",
    ),
    (
        "recovery",
        "delta_ref",
        "Data synchronization method record",
        "Selected application/file delta or cold-export method, scope and owner acceptance. "
        "Record an explicit cold-export decision when no delta is used.",
    ),
    (
        "recovery",
        "writer_fencing_ref",
        "Application writer isolation procedure",
        "How source and destination writers are fenced at cutover, with independent verification.",
    ),
    (
        "recovery",
        "traffic_ref",
        "Traffic switch and policy validation procedure",
        "Approved traffic change plus application tests and allowed/denied network-path "
        "verification.",
    ),
    (
        "recovery",
        "restore_ref",
        "Backup and restore validation record",
        "Restoration of application data, attachments and dependencies, with retained "
        "original results.",
    ),
    (
        "recovery",
        "recovery_ref",
        "Recovery before and after destination writes",
        "Separate source-return and post-write recovery procedures, including data reconciliation.",
    ),
    (
        "recovery",
        "retention_ref",
        "Retirement and retention authorization",
        "Owner-approved retention of source data and keys, deletion authority and cleanup "
        "verification.",
    ),
    (
        "targets",
        "objectives_ref",
        "Approved operating objectives record",
        "Accountable owner's acceptance of the targets below and representative workload "
        "used to measure them.",
    ),
    (
        "receiving",
        "campaign_ref",
        "Authorized qualification campaign",
        "Exact lab scope and campaign authorization for native Q05–Q10 observations.",
    ),
    (
        "receiving",
        "artifact_ref",
        "Installed release and artifact record",
        "Installed candidate digest, signed component versions, trust roots and mirror closure.",
    ),
    (
        "receiving",
        "security_ref",
        "Security findings and custody assessment",
        "Actual application-security results, required finding dispositions and "
        "jurisdiction/custody review.",
    ),
    (
        "receiving",
        "alert_ref",
        "Alert routing and escalation record",
        "Receiving route, acknowledgement objective, on-call rota and tested escalation evidence.",
    ),
    (
        "receiving",
        "receiving_team_ref",
        "Receiving team and independent reviewers",
        "Named operations, security, application and qualification reviewers with "
        "responsibilities and conflict checks.",
    ),
    (
        "receiving",
        "support_ref",
        "Support and operational rehearsal record",
        "Support ownership, operator rehearsal, patching, retained evidence and "
        "accessibility receiving checks.",
    ),
):
    reference(group, id_, label, help_)
for id_, label, help_, minimum, maximum in (
    (
        "max_outage_seconds",
        "Maximum application outage (seconds)",
        "Owner-approved outage limit. Zero means no outage is permitted.",
        0,
        604800,
    ),
    (
        "max_data_loss_bytes",
        "Maximum data loss (bytes)",
        "Owner-approved data-loss limit. Zero means no data loss is permitted.",
        0,
        9007199254740991,
    ),
    (
        "recovery_time_seconds",
        "Recovery time objective (seconds)",
        "Maximum accepted time to recover the service after a failure.",
        1,
        2592000,
    ),
    (
        "max_active_migrations",
        "Maximum simultaneous migrations",
        "Planning limit for the representative workload; admission still requires current "
        "measurements.",
        1,
        1000,
    ),
):
    FIELDS.append(
        {
            "id": id_,
            "group": "targets",
            "label": label,
            "help": help_,
            "kind": "integer",
            "minimum": minimum,
            "maximum": maximum,
        }
    )


def validate_values(values: Any) -> None:
    shape(values, set(), {field["id"] for field in FIELDS})
    for field in FIELDS:
        key = field["id"]
        if key not in values:
            continue
        value = values[key]
        if field["kind"] == "integer":
            if type(value) is not int or not field["minimum"] <= value <= field["maximum"]:
                raise Rejected("invalid_operator_target")
        elif (
            not isinstance(value, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,239}", value)
            or "-----BEGIN" in value
        ):
            raise Rejected("invalid_operator_reference")
    writers = {
        values[key]
        for key in ("source_writer_ref", "target_writer_ref", "image_writer_ref")
        if key in values
    }
    observers = {
        values[key]
        for key in ("source_observer_ref", "target_observer_ref", "image_observer_ref")
        if key in values
    }
    if writers & observers:
        raise Rejected("independent_verification_account_required")


def missing_fields(values: dict[str, Any]) -> list[str]:
    return [field["id"] for field in FIELDS if field["id"] not in values]
