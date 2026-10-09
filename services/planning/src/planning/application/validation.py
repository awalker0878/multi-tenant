"""Required immutable owner validation, composed before Planning is constructed."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Never

from planning.domain.model import Actor, Rejected, digest


@dataclass(frozen=True, slots=True)
class NativeValidation:
    recipes: Callable[[Actor, str, str], dict[str, Any]]
    clock: Callable[[], int]

    def __post_init__(self) -> None:
        if not callable(self.recipes) or not callable(self.clock):
            raise ValueError("required_native_validation")

    def current(self, plan: dict[str, Any]) -> None:
        content, binding = plan["content"], plan["binding"]
        scope, native = content["scope"], content["native_provisioning"]
        actor = Actor(
            scope["tenant_id"],
            binding["requested_by"],
            "plan.read",
            scope["resource_id"],
            scope["environment"],
        )
        recipe = self.recipes(actor, scope["site_id"], native["recipe_id"])
        if (
            digest(recipe) != native["recipe_sha256"]
            or min(recipe["expires_at"], content["valid_until"], content["input_fresh_until"])
            <= self.clock()
        ):
            raise Rejected("native_recipe_changed", 423)


@dataclass(frozen=True, slots=True)
class MigrationValidation:
    prepare: Callable[..., dict[str, Any]]
    recipes: Callable[[Actor, str, str], dict[str, Any]]
    support: Callable[[Actor, str, dict[str, Any]], dict[str, Any]]
    clock: Callable[[], int]

    def __post_init__(self) -> None:
        if not all(
            callable(value) for value in (self.prepare, self.recipes, self.support, self.clock)
        ):
            raise ValueError("required_migration_validation")

    def execution_current(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Service-only read checks recipe revocation without borrowing a user delegation."""
        scope = plan["content"]["scope"]
        actor = Actor(
            scope["tenant_id"],
            plan["binding"]["requested_by"],
            "plan.read",
            scope["resource_id"],
            scope["environment"],
        )
        composition = plan["content"]["native_migration"]
        readiness = self.support(actor, scope["site_id"], composition["migration"])
        if (
            not isinstance(readiness, dict)
            or readiness.get("status") != "eligible"
            or readiness.get("holds") != []
            or readiness.get("native_write_authorized") is not False
        ):
            raise Rejected("migration_readiness_held", 423)
        recipe = self.recipes(actor, scope["site_id"], composition["recipe_id"])
        if digest(recipe) != composition["recipe_sha256"] or recipe["expires_at"] <= self.clock():
            raise Rejected("migration_recipe_changed", 423)
        return readiness

    def current(self, actor: Actor, plan: dict[str, Any], delegations: dict[str, str]) -> None:
        content = plan["content"]
        site = content["scope"]["site_id"]
        composition = content["native_migration"]
        recipe = self.recipes(actor, site, composition["recipe_id"])
        if digest(recipe) != composition["recipe_sha256"] or recipe["expires_at"] <= self.clock():
            raise Rejected("migration_recipe_changed", 423)
        migration = composition["migration"]
        self.support(actor, site, migration)
        bound = self.prepare(
            actor.tenant,
            actor.application,
            actor.environment,
            site,
            migration["review"]["revision"],
            migration["review"]["digest"],
            delegations.get(site, ""),
            [
                {k: disk[k] for k in ("source_disk_sha256", "target_key", "format")}
                for disk in migration["disks"]
            ],
            action="plan.read",
        )
        if any(digest(migration.get(k)) != digest(v) for k, v in bound.items()):
            raise Rejected("migration_profiles_changed", 423)


def unavailable(*args: Any, **kwargs: Any) -> Never:
    raise Rejected("validation_authority_unavailable", 503)


@dataclass(frozen=True, slots=True)
class PlanValidation:
    native: NativeValidation
    migration: MigrationValidation
    support_current: Callable[[dict[str, Any]], None]

    def __post_init__(self) -> None:
        if not isinstance(self.native, NativeValidation) or not isinstance(
            self.migration, MigrationValidation
        ):
            raise ValueError("required_plan_validation")
        if not callable(self.support_current):
            raise ValueError("required_support_validation")

    @classmethod
    def unavailable(cls, clock: Callable[[], int]) -> "PlanValidation":
        """Explicit deny authority for facts-only consumers and non-native test fixtures."""
        return cls(
            NativeValidation(unavailable, clock),
            MigrationValidation(unavailable, unavailable, unavailable, clock),
            unavailable,
        )
