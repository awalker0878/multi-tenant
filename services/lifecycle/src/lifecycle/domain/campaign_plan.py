"""Validate immutable Planning evidence before deriving campaign admission inputs."""

from typing import Any

from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected
from lifecycle.domain.native_workflow import exact


def plan_requirements(record: dict[str, Any], ref: dict[str, Any], tenant: str) -> dict[str, Any]:
    """Reject incomplete or modified owner plans; no schedule assertion fills missing inputs."""
    binding = record.get("binding", {})
    content = record.get("content", {})
    if (
        record.get("invalidated") is not False
        or binding.get("plan_id") != ref["plan_id"]
        or binding.get("revision") != ref["plan_revision"]
        or binding.get("digest") != ref["plan_digest"]
        or binding.get("digest") != digest({k: v for k, v in binding.items() if k != "digest"})
        or binding.get("content_digest") != digest(content)
        or binding.get("tenant_id") != tenant
        or content.get("action") != "application.migrate"
        or content.get("execution_ready") is not True
        or binding.get("lane") != "operational"
    ):
        raise Rejected("complete_current_migration_plan_required", 423)
    requirements = exact(
        content.get("migration_campaign"), {"route_sha256", "sizes", "demands", "mode", "method"}
    )
    return {
        "scope": {k: binding[k] for k in ("site_id", "environment", "resource_id")},
        "requested_by": binding["requested_by"],
        "requirements": requirements,
    }
