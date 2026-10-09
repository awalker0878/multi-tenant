"""Bounded, authenticated read of currently published source-intent evidence."""

import time
from typing import Any

from planning.domain.model import Actor, Rejected, identifier, integer, sha
from planning.domain.workload_reconciliation import evaluate
from planning.infrastructure.owners import request


def current_workload_reconciliation(
    actor: Actor, site: str, binding: dict[str, Any],
    flow_e4: dict[str, Any] | None,
) -> dict[str, Any]:
    scope = {
        "tenant_id": identifier(actor.tenant),
        "application_id": identifier(actor.application),
        "environment_id": identifier(actor.environment),
        "site_id": identifier(site),
    }
    review = binding.get("review")
    if not isinstance(review, dict) or set(review) != {"revision", "digest"}:
        raise Rejected("catalogue_native_review_reference_missing", 423)
    records = request(
        "INVENTORY", "GET",
        f"/internal/tenants/{scope['tenant_id']}/migration-inputs/"
        f"{scope['application_id']}/{scope['environment_id']}/"
        f"{scope['site_id']}/{integer(review['revision'], 1)}/"
        f"{sha(review['digest'])}",
        schema_name="migration-input-v3",
    )
    if (records.get("tenant_id") != scope["tenant_id"]
            or records.get("site_id") != scope["site_id"]
            or records.get("revision") != review["revision"]
            or records.get("digest") != review["digest"]):
        raise Rejected("catalogue_native_inventory_owner_scope_changed", 423)
    published = request(
        "CATALOGUE", "GET",
        f"/internal/tenants/{scope['tenant_id']}/applications/"
        f"{scope['application_id']}/environments/{scope['environment_id']}"
        "/current-planning-intent",
        schema_name="catalogue-current-v1",
    )
    if published["intent"]["environment"]["id"] != scope["environment_id"]:
        raise Rejected("catalogue_native_current_intent_scope_changed", 423)
    return evaluate(scope, published, records, binding, flow_e4, int(time.time()))
