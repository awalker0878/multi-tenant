"""Live Inventory owner read; no profile or confirmation may come from a client body."""

import time
from typing import Any

from planning.domain.migration import bind_migration
from planning.domain.model import identifier, integer, sha
from planning.infrastructure.owners import request


def prepare_migration(
    tenant: str,
    application: str,
    environment: str,
    site: str,
    revision: int,
    content_digest: str,
    delegation: str,
    mapping: list[dict[str, Any]],
    action: str = "plan.create",
) -> dict[str, Any]:
    if action not in {"plan.create", "plan.read"}:
        from planning.domain.model import Rejected

        raise Rejected("migration_read_action_denied", 403)
    path = (
        f"/v1/tenants/{identifier(tenant)}/migration-inputs/{identifier(application)}/"
        f"{identifier(environment)}/{identifier(site)}/{integer(revision, 1)}/{sha(content_digest)}"
    )
    inputs = request(
        "INVENTORY",
        "GET",
        path,
        delegation=delegation,
        action=action,
        schema_name="migration-input-v4",
    )
    if (inputs["tenant_id"], inputs["site_id"], inputs["revision"], inputs["digest"]) != (
        tenant,
        site,
        revision,
        content_digest,
    ):
        from planning.domain.model import Rejected

        raise Rejected("migration_input_scope_mismatch", 403)
    return bind_migration(inputs, mapping, int(time.time()))
