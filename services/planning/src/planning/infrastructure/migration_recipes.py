"""Separately commissioned recipes. Clients choose IDs, never native connection or plan bytes."""

import os
import stat
from pathlib import Path
from typing import Any

from planning.domain.model import Actor, Rejected, decode, identifier, shape


def visible_recipes(
    actor: Actor, site: str, *, file_variable: str = "PLANNING_MIGRATION_RECIPES_FILE"
) -> list[dict[str, Any]]:
    try:
        path = Path(os.environ[file_variable])
        if not path.is_absolute() or any(p.is_symlink() for p in [path, *path.parents]):
            raise ValueError
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022 or info.st_size > 2097152:
                raise ValueError
            data = decode(stream.read(2097153))
        shape(data, {"schema_version", "recipes"})
        if (
            type(data["schema_version"]) is not int
            or data["schema_version"] != 1
            or not isinstance(data["recipes"], list)
            or not 1 <= len(data["recipes"]) <= 256
        ):
            raise ValueError
        matches = []
        seen = set()
        for row in data["recipes"]:
            shape(row, {"id", "recipe"})
            key = identifier(row["id"])
            if key in seen:
                raise ValueError
            seen.add(key)
            scope = row["recipe"]["scope"]
            if all(
                scope.get(k) == v
                for k, v in {
                    "tenant_id": actor.tenant,
                    "site_id": site,
                    "resource_id": actor.application,
                    "environment": actor.environment,
                }.items()
            ):
                matches.append(row)
        return matches
    except Rejected:
        raise
    except (KeyError, TypeError, ValueError, OSError):
        raise Rejected("migration_recipes_unavailable", 503) from None


def recipe_for(
    actor: Actor,
    site: str,
    recipe_id: str,
    *,
    file_variable: str = "PLANNING_MIGRATION_RECIPES_FILE",
) -> dict[str, Any]:
    matches = [
        r["recipe"]
        for r in visible_recipes(actor, site, file_variable=file_variable)
        if r["id"] == recipe_id
    ]
    if len(matches) != 1:
        # Absence and foreign scope are deliberately indistinguishable.
        raise Rejected("migration_recipe_unavailable", 423)
    return dict(matches[0])
