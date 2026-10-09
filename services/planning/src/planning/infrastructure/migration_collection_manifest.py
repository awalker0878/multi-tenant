"""Installed, protected per-release collection manifest binding.

Planning independently knows every field expected from Inventory. A signed
Inventory summary cannot decide its own completeness. The release allowlist
must be provisioned independently of browser submissions and Inventory.
"""
import os
import re
import stat
from pathlib import Path
from typing import Any

from planning.domain.model import digest


def _document(value: str, limit: int) -> dict[str, Any]:
    from planning.domain.model import decode
    path = Path(value)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("unprotected_migration_manifest_path")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022
                or info.st_size > limit):
            raise ValueError("unprotected_migration_manifest_file")
        data = decode(handle.read(limit + 1))
    if not isinstance(data, dict):
        raise ValueError("invalid_collection_manifest")
    return data


def binding(release_sha256: str) -> dict[str, Any] | None:
    """Return expected scoped attributes for one explicitly enrolled release."""
    try:
        path = os.environ["PLANNING_MIGRATION_COLLECTION_REGISTRY_FILE"]
        registry = _document(path, 32768)
        if (set(registry) != {"schema_version", "manifest_file",
                              "manifest_sha256", "releases"}
                or registry["schema_version"] != 1
                or not isinstance(registry["releases"], list)
                or not 1 <= len(registry["releases"]) <= 256
                or len(set(registry["releases"])) != len(registry["releases"])
                or not all(isinstance(x, str) and re.fullmatch(r"[a-f0-9]{64}", x)
                           for x in registry["releases"])
                or not isinstance(registry["manifest_sha256"], str)
                or not re.fullmatch(r"[a-f0-9]{64}", registry["manifest_sha256"])
                or release_sha256 not in registry["releases"]):
            return None
        manifest = _document(registry["manifest_file"], 262144)
        if manifest.get("schema_version") != 1 or digest(manifest) != registry["manifest_sha256"]:
            return None
        platforms: dict[str, dict[str, list[str]]] = {}
        for platform in ("vmware", "ahv", "openstack"):
            group = manifest["platforms"][platform]
            rows = group["attributes"]
            if not isinstance(rows, list) or not 1 <= len(rows) <= 256:
                return None
            scoped = {}
            for side in ("source", "target", "owner"):
                ids = [r["id"] for r in rows if r["scope"] == side]
                if len(ids) != len(set(ids)):
                    return None
                scoped[side] = sorted(ids)
            platforms[platform] = scoped
        return {"release_sha256": release_sha256,
                "manifest_sha256": registry["manifest_sha256"],
                "platforms": platforms}
    except (KeyError, OSError, TypeError, ValueError, IndexError):
        return None
