"""Discover deployed contract copies from executable code, independently of the registry.

Every shipped JSON contract copy must be owned by one active canonical release.
This catches stale packaged copies even when no executable source references them.
"""
from __future__ import annotations

import ast
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
    # Python packages use importlib.resources instead of PHP-style resources.
    for family in ("services", "workers"):
        for component in (root / family).glob("*"):
            for infrastructure in (component / "src").glob("*/infrastructure"):
                for subdir in ("inputs", "contracts", "messaging"):
                    folder = infrastructure / subdir
                    if folder.is_dir():
                        yield from folder.glob("*.json")


def executable_contract_loads(source: Path) -> set[str]:
    """Recognize actual JSON reads/imports, never arbitrary filename comments."""
    body = source.read_text(encoding="utf-8")
    if source.suffix == ".py":
        tree = ast.parse(body, filename=str(source))
        loaded = set()
        for call in ast.walk(tree):
            if (not isinstance(call, ast.Call)
                    or not isinstance(call.func, ast.Attribute)
                    or call.func.attr not in {"read_text", "read_bytes"}):
                continue
            for child in ast.walk(call.func.value):
                if (isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Attribute)
                        and child.func.attr == "joinpath"):
                    loaded.update(
                        value.value for arg in child.args
                        for value in ast.walk(arg)
                        if isinstance(value, ast.Constant) and isinstance(value.value, str)
                        and value.value.endswith(".json")
                    )
        return loaded
    if source.suffix == ".php":
        return {
            name
            for line in body.splitlines()
            if "file_get_contents(" in line
            and not line.lstrip().startswith(("//", "#", "*", "/*"))
            for name in FILENAME.findall(line)
        }
    if source.suffix in {".ts", ".vue"}:
        return {
            name
            for line in body.splitlines()
            if re.search(r"^\\s*import\\s+(?!type\\b).*?\\sfrom\\s+['\\\"]", line)
            for name in FILENAME.findall(line)
        }
    return set()


def discover_runtime_copies(root: Path = ROOT) -> dict[str, list[str]]:
    copies = sorted(deployed_copies(root))
    by_name: dict[str, list[Path]] = {}
    for artifact in copies:
        by_name.setdefault(artifact.name, []).append(artifact)
    usages: dict[str, set[str]] = {}
    for source in runtime_sources(root):
        names = executable_contract_loads(source)
        for name in names & by_name.keys():
            for artifact in by_name[name]:
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
    shipped = {str(path.relative_to(root)) for path in deployed_copies(root)}
    unregistered = shipped - indexed.keys()
    if unregistered:
        raise ValueError("Shipped contract copies missing from active releases: " + repr(sorted(unregistered)))
    missing = {path: sources for path, sources in observed.items() if path not in indexed}
    if missing:
        raise ValueError("Runtime contract copies missing from active releases: " + repr(missing))

    # Installed copies must have executable consumers. Planning resolves schema
    # names through its typed operation map, rather than literal filenames.
    owner_map = root / "services/planning/src/planning/infrastructure/owner_contracts.py"
    owner_loader = root / "services/planning/src/planning/infrastructure/owners.py"
    dynamic_map = owner_map.read_text(encoding="utf-8") if owner_map.is_file() else ""
    dynamic_loader = owner_loader.read_text(encoding="utf-8") if owner_loader.is_file() else ""
    dynamic_ready = 'joinpath(name + ".json")' in dynamic_loader and "contract_for_operation" in dynamic_loader
    unconsumed = []
    for artifact in indexed:
        if artifact in observed:
            continue
        prefix = "services/planning/src/planning/infrastructure/inputs/"
        if (artifact.startswith(prefix) and dynamic_ready
                and ('"' + Path(artifact).stem + '"') in dynamic_map):
            continue
        unconsumed.append(artifact)
    if unconsumed:
        raise ValueError("Registered installed contracts have no executable consumer: " + repr(sorted(unconsumed)))

    # Check every registered copy, including dynamically loaded input schemas.
    for artifact, canonical in indexed.items():
        if not (root / canonical).is_file():
            raise ValueError(f"Runtime contract canonical missing: {canonical}")
        if (root / artifact).read_bytes() != (root / canonical).read_bytes():
            raise ValueError(f"Runtime contract copy drift: {artifact} != {canonical}")
    return observed
