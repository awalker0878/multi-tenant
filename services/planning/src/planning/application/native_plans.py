"""Immutable P07 proposals and unattended recipe revocation checks."""

from typing import Any
from uuid import uuid4

from planning.application.planning import Planning
from planning.application.validation import NativeValidation
from planning.domain.compilation import bind
from planning.domain.model import Actor, Rejected, digest, identifier, shape
from planning.domain.native_plan import compose_native


class NativePlans:
    def __init__(self, planning: Planning, validation: NativeValidation) -> None:
        if validation is not planning.validation.native:
            raise ValueError("native_validation_composition_mismatch")
        self.planning, self.validation = planning, validation

    def current(self, plan: dict[str, Any]) -> None:
        self.validation.current(plan)

    def create(
        self, actor: Actor, body: dict[str, Any], key: str, delegation: str
    ) -> dict[str, Any]:
        shape(body, {"site_id", "base_plan_id", "recipe_id"})
        site = identifier(body["site_id"])
        for field in ("base_plan_id", "recipe_id"):
            identifier(body[field])
        identifier(key)
        fingerprint = digest(
            {
                "operation": "native_plan",
                "application": actor.application,
                "environment": actor.environment,
                "body": body,
            }
        )
        with self.planning.database.transaction() as tx:
            prior = self.planning.retry(tx, actor, key, fingerprint)
            if prior:
                return prior
        base = self.planning.get(
            actor.tenant, actor.application, actor.environment, body["base_plan_id"], "plan"
        )
        if (
            base["content"]["scope"]["site_id"] != site
            or base["binding"]["requested_by"] != actor.actor
            or base["binding"]["content_digest"] != digest(base["content"])
        ):
            raise Rejected("native_base_plan_scope_denied", 403)
        if self.planning.validity(actor, base, {site: delegation})["current"] is not True:
            raise Rejected("current_qualified_base_plan_required", 423)
        recipe = self.validation.recipes(actor, site, body["recipe_id"])
        content = compose_native(base["content"], recipe, self.planning.clock())
        content["native_provisioning"].update(base_plan_id=base["id"], recipe_id=body["recipe_id"])
        plan_id = str(uuid4())
        payload = {
            **base,
            "id": plan_id,
            "content": content,
            "binding": bind(content, plan_id, actor.actor),
        }
        return self.planning.save(actor, key, fingerprint, "plan", payload)
