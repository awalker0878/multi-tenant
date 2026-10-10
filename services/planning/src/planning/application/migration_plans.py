"""Immutable complete migration proposals with exact retries and current owner reads."""

from collections.abc import Callable
from typing import Any
from uuid import uuid4

from planning.application.planning import Planning
from planning.application.validation import MigrationValidation
from planning.domain.compilation import bind
from planning.domain.migration_plan import compose_migration
from planning.domain.migration_api_selection import pin as pin_api_selection
from planning.domain.model import Actor, Rejected, digest, identifier, integer, sha, shape


class MigrationPlans:
    def __init__(
        self,
        planning: Planning,
        validation: MigrationValidation,
        available: Callable[[Actor, str], list[dict[str, Any]]] | None = None,
    ) -> None:
        if validation is not planning.validation.migration:
            raise ValueError("migration_validation_composition_mismatch")
        self.planning, self.validation = planning, validation
        self.available = available

    def options(self, actor: Actor, body: dict[str, Any], delegation: str) -> dict[str, Any]:
        """Return only currently composable choices; never expose registry paths or intents."""
        shape(body, {"site_id", "review", "disks"})
        site = identifier(body["site_id"])
        review = shape(body["review"], {"revision", "digest"})
        bound = self.validation.prepare(
            actor.tenant,
            actor.application,
            actor.environment,
            site,
            integer(review["revision"], 1),
            sha(review["digest"]),
            delegation,
            body["disks"],
        )
        self.validation.support(actor, site, bound)
        if self.available is None:
            raise Rejected("migration_recipes_unavailable", 503)
        candidates = [
            r
            for r in self.available(actor, site)
            if r["recipe"].get("source_identity_sha256")
            == bound["source"]["native_identity_sha256"]
            and r["recipe"].get("target_identity_sha256")
            == bound["target"]["native_identity_sha256"]
            and r["recipe"].get("method") == bound["method"]
        ]
        if len(candidates) > 8:
            raise Rejected("migration_recipe_selection_bound", 423)
        options = []
        for row in candidates:
            recipe = row["recipe"]
            with self.planning.database.transaction() as tx:
                base = tx.one(
                    "SELECT payload FROM app.planning_records WHERE tenant=%s AND actor=%s "
                    "AND application=%s AND environment=%s AND kind='plan' "
                    "AND payload->'binding'->>'content_digest'=%s "
                    "ORDER BY created_at DESC,id LIMIT 1",
                    (
                        actor.tenant,
                        actor.actor,
                        actor.application,
                        actor.environment,
                        sha(recipe["base_content_sha256"]),
                    ),
                )
            if base is None:
                continue
            try:
                plan = base["payload"]
                if self.planning.validity(actor, plan, {site: delegation})["current"] is not True:
                    continue
                content = compose_migration(plan["content"], bound, recipe, self.planning.clock())
                self.validation.support(actor, site, content["native_migration"]["migration"])
            except Rejected as error:
                if error.status in {401, 403, 404}:
                    raise
                continue
            options.append(
                {
                    "recipe_id": row["id"],
                    "base_plan_id": plan["id"],
                    "mode": recipe["mode"],
                    "method": recipe["method"],
                    "expires_at": content["valid_until"],
                    "stages": len(content["effects"]),
                }
            )
        return {"items": options, "native_write_authorized": False}

    def execution_current(self, plan: dict[str, Any]) -> None:
        self.validation.execution_current(plan)

    def current(self, actor: Actor, plan: dict[str, Any], delegations: dict[str, str]) -> None:
        self.validation.current(actor, plan, delegations)

    def create(
        self, actor: Actor, body: dict[str, Any], key: str, delegation: str
    ) -> dict[str, Any]:
        shape(body, {"site_id", "base_plan_id", "recipe_id", "review", "disks"})
        site = identifier(body["site_id"])
        identifier(body["base_plan_id"])
        identifier(body["recipe_id"])
        review = shape(body["review"], {"revision", "digest"})
        integer(review["revision"], 1)
        sha(review["digest"])
        fingerprint = digest(
            {
                "operation": "migration_plan",
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
            raise Rejected("migration_base_plan_scope_denied", 403)
        if self.planning.validity(actor, base, {site: delegation})["current"] is not True:
            raise Rejected("current_qualified_base_plan_required", 423)
        bound = self.validation.prepare(
            actor.tenant,
            actor.application,
            actor.environment,
            site,
            review["revision"],
            review["digest"],
            delegation,
            body["disks"],
        )
        self.validation.support(actor, site, bound)
        recipe = self.validation.recipes(actor, site, body["recipe_id"])
        content = compose_migration(base["content"], bound, recipe, self.planning.clock())
        admitted = self.validation.support(actor, site, content["native_migration"]["migration"])
        content["native_migration"]["api_selection"] = pin_api_selection(
            admitted, self.planning.clock()
        )
        content["native_migration"].update(base_plan_id=base["id"], recipe_id=body["recipe_id"])
        plan_id = str(uuid4())
        payload = {
            **base,
            "id": plan_id,
            "content": content,
            "binding": bind(content, plan_id, actor.actor),
        }
        return self.planning.save(actor, key, fingerprint, "plan", payload)
