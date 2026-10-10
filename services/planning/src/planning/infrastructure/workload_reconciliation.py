"""Bounded, authenticated read of currently published source-intent evidence."""

import time
from typing import Any

from planning.domain.model import Actor, Rejected, identifier, integer, sha
from planning.domain.workload_reconciliation import evaluate
from planning.infrastructure.owners import request


def current_review_binding(
    actor: Actor, site: str, review: dict[str, Any],
) -> dict[str, Any]:
    """Resolve selected migration review from authenticated Inventory custody.

    The browser supplies only an immutable revision/digest locator. Native
    identities, platforms, profile SHA and method are never user declarations.
    """
    if not isinstance(review, dict) or set(review) != {"revision", "digest"}:
        raise Rejected("migration_review_locator_required", 422)
    revision = integer(review["revision"], 1)
    review_sha = sha(review["digest"])
    records = request(
        "INVENTORY", "GET",
        f"/internal/tenants/{identifier(actor.tenant)}/migration-inputs/"
        f"{identifier(actor.application)}/{identifier(actor.environment)}/"
        f"{identifier(site)}/{revision}/{review_sha}",
        schema_name="migration-input-v4",
    )
    if (records.get("tenant_id") != actor.tenant
            or records.get("site_id") != site
            or records.get("revision") != revision
            or records.get("digest") != review_sha
            or records.get("current") is not True
            or not isinstance(records.get("source"), dict)
            or not isinstance(records.get("target"), dict)):
        raise Rejected("migration_current_review_unavailable", 423)
    return {
        "source": records["source"], "target": records["target"],
        "method": records["method"], "review": review,
    }


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
        schema_name="migration-input-v4",
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
    return {
        "reconciliation": evaluate(scope, published, records, binding, flow_e4, int(time.time())),
        "collection_coverages": records.get("collection_coverages", []),
    }
