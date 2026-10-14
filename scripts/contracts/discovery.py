"""Independent, current contract dependency discovery shared by integrity gates.

Canonical references are resolved locally, including URI schema identities and
embedded schemas. Evidence is typed: source/test mentions are never promoted to
executable runtime use or to built-artifact qualification.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

AREAS = ("openapi", "asyncapi", "schemas", "capabilities", "platforms")
IGNORED = {".git", ".venv", "vendor", "node_modules", "__pycache__", "build", "dist"}
REPORTS = {
    "architecture/contract-release-inventory.json",
    "architecture/contract-dependencies.json",
}
REFERENCE = re.compile(
    r"contracts/(?:openapi|asyncapi|schemas|capabilities|platforms)/[A-Za-z0-9_./-]+\.(?:json|ya?ml)"
)


def read(path: Path):
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text) if path.suffix in {".yaml", ".yml"} else json.loads(text)


def canonical_paths(root: Path) -> set[str]:
    return {
        str(path.relative_to(root))
        for area in AREAS
        for path in (root / "contracts" / area).rglob("*")
        if path.is_file() and path.suffix in {".json", ".yaml", ".yml"}
    }


def walk(node):
    yield node
    if isinstance(node, dict):
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def pointer(document, fragment: str, label: str):
    if not fragment:
        return document
    fragment = unquote(fragment)
    if not fragment.startswith("/"):
        if any(
            isinstance(node, dict) and fragment in {node.get("$anchor"), node.get("$dynamicAnchor")}
            for node in walk(document)
        ):
            return document
        raise ValueError(f"Unresolved contract anchor: {label}#{fragment}")
    value = document
    try:
        for segment in fragment[1:].split("/"):
            key = segment.replace("~1", "/").replace("~0", "~")
            value = value[int(key)] if isinstance(value, list) else value[key]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise ValueError(f"Unresolved contract pointer: {label}#{fragment}") from error
    return value


def canonical_dependencies(root: Path) -> dict[str, set[str]]:
    """Discover edges from specifications, data profiles and generation inputs."""
    documents = {path: read(root / path) for path in sorted(canonical_paths(root))}
    identities = {}
    for path, document in documents.items():
        if not isinstance(document, dict):
            raise ValueError(f"Invalid canonical document: {path}")
        identifier = document.get("$id")
        if identifier:
            if identifier in identities:
                raise ValueError(f"Duplicate canonical schema identity: {identifier}")
            identities[identifier] = path
    edges = {path: set() for path in documents}

    def schema_projection(value, *, top=True):
        if isinstance(value, dict):
            projected = {
                key: schema_projection(child, top=False)
                for key, child in value.items()
                if not (top and key in {"$schema", "$id", "title"})
            }
            ref = projected.get("$ref")
            if isinstance(ref, str):
                projected["$ref"] = re.sub(r"^#/components/schemas/[^/]+/\$defs/", "#/$defs/", ref)
            return projected
        if isinstance(value, list):
            return [schema_projection(child, top=False) for child in value]
        return value

    schema_sources = {
        path: schema_projection(document)
        for path, document in documents.items()
        if path.startswith("contracts/schemas/")
    }
    for path, document in documents.items():
        embedded_schemas = [
            *document.get("components", {}).get("schemas", {}).values(),
            *document.get("$defs", {}).values(),
        ]
        for embedded in embedded_schemas:
            projected = schema_projection(embedded)
            edges[path].update(
                source
                for source, value in schema_sources.items()
                if source != path and projected == value
            )
        for node in walk(document):
            if isinstance(node, str):
                # Capability source_manifest/source_crosswalk and other explicit
                # canonical paths are dependencies even when they are not $ref.
                edges[path].update(p for p in REFERENCE.findall(node) if p != path)
                continue
            if not isinstance(node, dict):
                continue
            embedded = identities.get(node.get("$id"))
            if embedded and embedded != path:
                edges[path].add(embedded)
            for keyword in ("$ref", "$dynamicRef"):
                reference = node.get(keyword)
                if reference is None:
                    continue
                if not isinstance(reference, str):
                    raise ValueError(f"Non-string {keyword}: {path}")
                address, _, fragment = reference.partition("#")
                if not address:
                    # OpenAPI/AsyncAPI pointers bind to the containing document.
                    pointer(document, fragment, path)
                    continue
                dependency = identities.get(address)
                if dependency is None:
                    uri = urlsplit(address)
                    if uri.scheme or uri.netloc:
                        raise ValueError(
                            f"Unresolved external contract reference: {path} -> {reference}"
                        )
                    resolved = (root / path).parent.joinpath(unquote(address)).resolve()
                    if not resolved.is_relative_to(root.resolve()):
                        raise ValueError(f"Escaping canonical reference: {path} -> {reference}")
                    dependency = str(resolved.relative_to(root.resolve()))
                if dependency not in documents:
                    raise ValueError(f"Missing executable dependency: {path} -> {dependency}")
                pointer(documents[dependency], fragment, dependency)
                if dependency != path:
                    edges[path].add(dependency)
        kind = path.split("/")[1]
        if kind == "capabilities":
            edges[path].add("contracts/schemas/capabilities/" + Path(path).name)
        elif kind == "platforms":
            edges[path].add("contracts/schemas/platforms/source-profile-v1.json")

    # Embedded projections need dependencies even when normalization removes
    # the source $id. Read the generator's literal table rather than repeat it.
    generator = root / "scripts/contracts/generate_authority_releases.py"
    if generator.is_file():
        tree = ast.parse(generator.read_text())
        tables = [
            ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "RELEASES" for t in node.targets)
        ]
        if len(tables) != 1:
            raise ValueError("Missing authoritative embedded-schema generation table")
        for name, components in tables[0].items():
            target = "contracts/openapi/" + name
            if target not in edges:
                raise ValueError(f"Orphaned authority generator: {target}")
            edges[target].update(components.values())
    readiness = root / "scripts/contracts/generate_readiness.py"
    if readiness.is_file():
        sources = REFERENCE.findall(readiness.read_text())
        if len(set(sources)) != 1:
            raise ValueError("Ambiguous readiness projection source")
        target = "contracts/openapi/planning-migration-v1.6.json"
        if target not in edges:
            raise ValueError(f"Orphaned readiness generator: {target}")
        edges[target].update(sources)
    for path, dependencies in edges.items():
        if path in dependencies:
            raise ValueError(f"Self-referential contract dependency: {path}")
        missing = dependencies - documents.keys()
        if missing:
            raise ValueError(f"Missing executable dependency: {path} -> {sorted(missing)}")
    return edges


def verify_dependencies(root: Path, registry: dict) -> dict[str, set[str]]:
    discovered = canonical_dependencies(root)
    releases = registry["active_releases"]
    paths = [row["path"] for row in releases]
    if len(paths) != len(set(paths)):
        raise ValueError("Duplicate active canonical contract release")
    if set(paths) != discovered.keys():
        raise ValueError(
            "Canonical inventory does not match active registry: "
            + repr(sorted(set(paths) ^ discovered.keys()))
        )
    for row in releases:
        declared = row.get("depends_on", [])
        if not isinstance(declared, list) or len(declared) != len(set(declared)):
            raise ValueError(f"Duplicate or invalid release dependencies: {row['path']}")
        if set(declared) != discovered[row["path"]]:
            raise ValueError(
                f"Canonical dependency declarations disagree: {row['path']}; "
                f"missing={sorted(discovered[row['path']] - set(declared))}; "
                f"orphaned={sorted(set(declared) - discovered[row['path']])}"
            )
    visiting, visited = set(), set()

    def visit(path):
        if path in visiting:
            raise ValueError(f"Circular canonical release dependency: {path}")
        if path in visited:
            return
        visiting.add(path)
        for child in discovered[path]:
            visit(child)
        visiting.remove(path)
        visited.add(path)

    for path in discovered:
        visit(path)
    return discovered


def verify_manifests(root: Path, registry: dict) -> dict[str, list[str]]:
    from build import assemble, safe_source_file

    releases = {row["path"]: row for row in registry["active_releases"]}
    targets, used = {}, set()
    for path in sorted((root / "contracts/source").rglob("manifest.json")):
        # build.assemble uses only the manifest directory; destination checks
        # stay in build.verify. This inventory is independently bidirectional.
        manifest, _ = assemble(path)
        target = manifest["target"]
        relative = str(path.relative_to(root))
        if target in targets:
            raise ValueError(f"Duplicate generation ownership: {target}")
        row = releases.get(target)
        if row is None or row.get("source_manifest") != relative:
            raise ValueError(f"Orphaned or undeclared source manifest: {relative}")
        copies = manifest.get("copies", [])
        if len(copies) != len(set(copies)) or set(copies) != set(row.get("copies", [])):
            raise ValueError(f"Manifest installed-copy bindings disagree: {relative}")
        fragments = [
            manifest["base"],
            *[name for part in manifest["parts"].values() for name in part["files"]],
        ]
        if len(fragments) != len(set(fragments)):
            raise ValueError(f"Duplicate source fragments: {relative}")
        targets[target] = [
            relative,
            *[str(safe_source_file(path.parent, name).relative_to(root)) for name in fragments],
        ]
        used.update(targets[target])
    files = {str(p.relative_to(root)) for p in (root / "contracts/source").rglob("*.json")}
    if files - used:
        raise ValueError(f"Orphaned contract source fragments: {sorted(files - used)}")
    for target, row in releases.items():
        if row.get("source_manifest") and target not in targets:
            raise ValueError(f"Missing registered source manifest: {target}")
    return targets


def repository_texts(root: Path):
    """Include code, generators, workers, CI, fixtures and packaging declarations."""
    for directory in (
        "apps",
        "services",
        "workers",
        "scripts",
        "tests",
        "contracts/source",
        "contracts/fixtures",
        "architecture",
        ".github",
        "deploy",
    ):
        for path in (root / directory).rglob("*"):
            if (
                not path.is_file()
                or any(
                    part in IGNORED or part.endswith(".egg-info")
                    for part in path.relative_to(root).parts
                )
                or str(path.relative_to(root)) in REPORTS
            ):
                continue
            if (
                path.suffix
                in {".py", ".php", ".ts", ".tsx", ".vue", ".json", ".yaml", ".yml", ".toml", ".sh"}
                or path.name == "Dockerfile"
            ):
                yield str(path.relative_to(root)), path.read_text(encoding="utf-8")


def reference_evidence(root: Path, paths: set[str]) -> dict[str, list[dict]]:
    """Audit mentions and generated digests; label tests/tools separately."""
    evidence = {path: [] for path in paths}
    hashes = {}
    for path in paths:
        if (root / path).is_file():
            raw = (root / path).read_bytes()
            hashes[path] = {hashlib.sha256(raw).hexdigest()}
            try:
                doc = read(root / path)
                hashes[path].add(
                    hashlib.sha256(
                        json.dumps(
                            doc, sort_keys=True, ensure_ascii=True, separators=(",", ":")
                        ).encode()
                    ).hexdigest()
                )
            except (ValueError, yaml.YAMLError):
                pass
    for source, text in repository_texts(root):
        if source in {
            "architecture/contract-consumers.json",
            "architecture/installed-contract-usage.json",
        }:
            continue  # Secondary declarations are not independent evidence.
        for path in paths:
            name = Path(path).name
            marker = path if path in text else name if name in text else None
            if marker is None:
                marker = next((digest for digest in hashes.get(path, ()) if digest in text), None)
            if marker:
                parts = Path(source).parts
                runtime = parts[0] in {"apps", "services", "workers"} and not set(
                    parts
                ).intersection({"tests", "fixtures", "verification"})
                evidence[path].append(
                    {
                        "source": source,
                        "kind": "runtime-source-reference"
                        if runtime
                        else "validation-or-generation",
                        "marker": marker,
                    }
                )
    return evidence


def retirement_references(
    root: Path, removed: set[str], prior: dict, old_usage: dict
) -> dict[str, list[str]]:
    """Use prior names/copies/loader keys so deleting declarations cannot hide use.

    Surviving historical consumers do not themselves prohibit retirement. Their
    old copies, literal and typed loader names, canonical IDs and generator refs
    must be absent from the current checkout. Built artifacts are independently
    checked in CI; this does not establish external deployment/consumer status.
    """
    blockers = {path: [] for path in removed}
    rows = {row["path"]: row for row in prior.get("active_releases", [])}
    texts = list(repository_texts(root))
    current_docs = {path: read(root / path) for path in canonical_paths(root)}
    current_registry = read(root / "architecture/contract-consumers.json")
    current_copies = {
        copy: release["path"]
        for release in current_registry["active_releases"]
        for copy in release.get("copies", [])
    }
    current_addresses = sorted(
        {
            address
            for current in current_docs
            for address in (current, "/".join(Path(current).parts[2:]))
        },
        key=len,
        reverse=True,
    )
    for path in sorted(removed):
        row = rows.get(path)
        if row is None:
            raise ValueError(f"Unregistered prior canonical release cannot be retired: {path}")
        tokens = {path, Path(path).name}
        copies = set(row.get("copies", [])) | {
            item.get("copy")
            for item in old_usage.get("copies", [])
            if item.get("canonical") == path and item.get("copy")
        }
        for copy in copies:
            replacement = current_copies.get(copy)
            # A generic package resource may retain its path after its contents
            # migrate to a new active canonical. A versioned retired filename
            # must never become an alias for the replacement release.
            if (
                replacement
                and replacement not in removed
                and not re.search(r"-v[0-9]", Path(copy).name)
                and (root / replacement).is_file()
                and (root / copy).is_file()
                and (root / copy).read_bytes() == (root / replacement).read_bytes()
            ):
                continue
            tokens.update({copy, Path(copy).name, Path(copy).stem})
            if (root / copy).exists():
                blockers[path].append("installed copies " + copy)
        for source, body in texts:
            # The current registries are dependencies too. Audit output and docs
            # are excluded from the scan; they cannot become retirement blockers.
            # Different owned schemas can share a basename (Inventory/Planning
            # fact-v1). An explicit surviving path disambiguates that mention.
            disambiguated = body
            for address in current_addresses:
                disambiguated = disambiguated.replace(address, "")
            hits = sorted(
                token
                for token in tokens
                if re.search(
                    r"(?<![A-Za-z0-9_.-])" + re.escape(token) + r"(?![A-Za-z0-9_.-])", disambiguated
                )
            )
            if hits:
                blockers[path].append(f"current reference {source}: {hits}")
        for source, doc in current_docs.items():
            body = json.dumps(doc)
            if any(
                re.search(r"(?<![A-Za-z0-9_.-])" + re.escape(token) + r"(?![A-Za-z0-9_.-])", body)
                for token in tokens
            ):
                blockers[path].append("dependent releases " + source)
    return blockers
