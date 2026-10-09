"""Discover deployed contract copies from executable code, independently of the registry.

Historical copies are permitted only while not referenced by deployed source.
This catches removal from *both* registry collections without trusting either.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOTS = (
    ("services", "app", {".php"}),
    ("services", "src", {".py"}),
    ("workers", "src", {".py"}),
    ("apps", "app", {".php"}),
    ("apps", "resources/js", {".ts", ".vue"}),
)
FILENAME = re.compile(r"(?<![A-Za-z0-9_.-])([A-Za-z0-9][A-Za-z0-9_.-]*\.json)(?![A-Za-z0-9_.-])")


def runtime_sources(root: Path):
    for family, subtree, extensions in SOURCE_ROOTS:
        for component in sorted((root / family).glob("*")):
            folder = component / subtree
            if not folder.is_dir():
                continue
            for source in folder.rglob("*"):
                if (source.is_file() and source.suffix in extensions
                        and not any(part in {"tests", "test", "fixtures", "node_modules", "vendor"}
                                    for part in source.relative_to(folder).parts)):
                    yield source


def deployed_copies(root: Path):
    for family in ("services", "apps", "workers"):
        for component in (root / family).glob("*"):
            directory = component / "resources/contracts"
            if directory.is_dir():
                yield from directory.glob("*.json")
    for subpath in (
        "services/planning/src/planning/infrastructure/inputs",
        "services/lifecycle/src/lifecycle/infrastructure/contracts",
    ):
        folder = root / subpath
        if folder.is_dir():
            yield from folder.glob("*.json")


def discover_runtime_copies(root: Path = ROOT) -> dict[str, list[str]]:
    copies = sorted(deployed_copies(root))
    by_name: dict[str, list[Path]] = {}
    for artifact in copies:
        by_name.setdefault(artifact.name, []).append(artifact)
    usages: dict[str, set[str]] = {}
    for source in runtime_sources(root):
        names = set(FILENAME.findall(source.read_text(encoding="utf-8")))
        for name in names & by_name.keys():
            for artifact in by_name[name]:
                # A different product's deployed package is not used merely
                # because two products ship a same-named historical file.
                if artifact.relative_to(root).parts[:2] != source.relative_to(root).parts[:2]:
                    continue
                path = str(artifact.relative_to(root))
                usages.setdefault(path, set()).add(str(source.relative_to(root)))
    return {path: sorted(sources) for path, sources in sorted(usages.items())}


def verify_runtime_inventory(registry: dict, root: Path = ROOT) -> dict[str, list[str]]:
    observed = discover_runtime_copies(root)
    indexed: dict[str, str] = {}
    for release in registry["active_releases"]:
        for artifact in release.get("copies", []):
            if artifact in indexed:
                raise ValueError(f"Runtime copy declared by multiple active releases: {artifact}")
            indexed[artifact] = release["path"]
    missing = {path: sources for path, sources in observed.items() if path not in indexed}
    if missing:
        raise ValueError("Runtime contract copies missing from active releases: " + repr(missing))
    # Prevent a self-consistent but false registry entry from mapping a file
    # to an unrelated canonical release or silently dropping its producer.
    for artifact in observed:
        canonical = indexed[artifact]
        if not (root / canonical).is_file():
            raise ValueError(f"Runtime contract canonical missing: {canonical}")
        if (root / artifact).read_bytes() != (root / canonical).read_bytes():
            raise ValueError(f"Runtime contract copy drift: {artifact} != {canonical}")
    return observed
