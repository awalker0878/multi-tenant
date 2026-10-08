"""Protected tranche selection; qualification is always read from Assurance custody."""

import os
import stat
from pathlib import Path
from typing import Any

from planning.domain.model import Actor, Rejected, decode, digest, identifier, shape
from planning.infrastructure.owners import request


def selected_tranche(actor: Actor, site: str) -> dict[str, Any]:
    try:
        path = Path(os.environ["PLANNING_MIGRATION_SUPPORT_FILE"])
        if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022 or info.st_size > 2097152:
                raise ValueError
            document = shape(decode(stream.read(2097153)), {"schema_version", "assignments"})
        if document["schema_version"] != 1 or not isinstance(document["assignments"], list):
            raise ValueError
        if len(document["assignments"]) > 256:
            raise ValueError
        expected = {
            "tenant_id": actor.tenant,
            "site_id": identifier(site),
            "resource_id": actor.application,
            "environment": actor.environment,
        }
        matches = []
        for row in document["assignments"]:
            shape(row, {"scope", "tranche"})
            shape(row["scope"], set(expected))
            if row["scope"] == expected:
                matches.append(row["tranche"])
        if len(matches) != 1:
            raise Rejected("migration_support_scope_unassigned", 423)
        return dict(matches[0])
    except Rejected:
        raise
    except (KeyError, TypeError, ValueError, OSError):
        raise Rejected("migration_support_unavailable", 503) from None


def qualification_records(
    actor: Actor, site: str, selected: dict[str, Any]
) -> list[dict[str, Any]]:
    scope = {
        "tenant_id": actor.tenant,
        "site_id": site,
        "resource_id": actor.application,
        "environment": actor.environment,
    }
    result = request(
        "ASSURANCE",
        "POST",
        f"/v1/tenants/{actor.tenant}/migration-qualifications",
        {
            "scope": scope,
            "tranche_sha256": digest(selected),
            "release_sha256": selected["release_sha256"],
        },
        schema_name="migration-support-v1",
    )
    if (
        result["scope"] != scope
        or result["tranche_sha256"] != digest(selected)
        or (result["release_sha256"] != selected["release_sha256"])
    ):
        raise Rejected("migration_support_scope_changed", 423)
    return list(result["records"])
