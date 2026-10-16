"""Derive contract change-impact edges from active releases and installed consumers.

Do not infer service call direction from the legacy architectural layering DAG:
wire, event, shared schema, capability and platform profile dependencies are
different relationships and may legitimately form cycles.
"""
from __future__ import annotations

from contract_io import read

import argparse
import json
from pathlib import Path

from artifact_attestation import COMPONENTS
from installed_usage import verify_installed_usage
from discovery import verify_dependencies, verify_manifests

ROOT = Path(__file__).resolve().parents[2]
TYPE = {
    "openapi": "http",
    "asyncapi": "event",
    "schemas": "schema",
    "capabilities": "capability",
    "platforms": "platform",
}


def derive(root: Path = ROOT) -> dict:
    registry = read(root / "architecture/contract-consumers.json")
    usage = read(root / "architecture/installed-contract-usage.json")
    copies = {item["copy"]: item for item in usage["copies"]}
    # A declared copy is not executable loader evidence: verify real imports.
    verify_installed_usage(root, registry)
    discovered = verify_dependencies(root, registry)
    verify_manifests(root, registry)
    edges = []
    release_dependencies = []
    producer_local = []
    installed_seen = set()
    active_paths = {item["path"] for item in registry["active_releases"]}
    for entry in registry["active_releases"]:
        canonical, owner = entry["path"], entry["owner"]
        kind = canonical.split("/")[1]
        if kind not in TYPE:
            raise ValueError(f"Unknown active contract classification: {canonical}")
        if not (root / canonical).is_file():
            raise ValueError(f"Missing active dependency source: {canonical}")
        for dependency in sorted(discovered[canonical]):
            if dependency == canonical or dependency not in active_paths:
                raise ValueError(f"Invalid active dependency: {canonical} -> {dependency}")
            release_dependencies.append({"release": canonical, "depends_on": dependency,
                                         "evidence": "independently-discovered"})
        declared_consumers = entry["consumers"]
        if len(declared_consumers) != len(set(declared_consumers)):
            raise ValueError(f"Duplicate consumers on: {canonical}")
        bindings = {}
        for copy in entry.get("copies", []):
            if copy not in copies or copies[copy]["canonical"] != canonical:
                raise ValueError(f"Unknown installed dependency: {copy}")
            component = "/".join(Path(copy).parts[:2])
            if component not in COMPONENTS:
                raise ValueError(f"Unknown runtime component for installed copy: {copy}")
            consumer = COMPONENTS[component][0]
            if consumer == owner:
                # Producer-installed schema is an internal encoding/validation
                # boundary, not a cross-service dependency.
                producer_local.append({
                    "provider": owner, "release": canonical, "copy": copy,
                    "kind": TYPE[kind],
                })
            elif consumer in declared_consumers:
                bindings.setdefault(consumer, []).append(copy)
            else:
                raise ValueError(f"Installed consumer omitted from release: {canonical} {consumer}")
            installed_seen.add(copy)
        for consumer in declared_consumers:
            if consumer == owner:
                raise ValueError(f"An owner is its own consumer: {canonical}")
            edges.append({
                "consumer": consumer, "provider": owner, "release": canonical,
                "kind": TYPE[kind],
                "installed_copies": sorted(bindings.get(consumer, [])),
                "evidence": "installed-loader" if consumer in bindings else "registry-declaration",
            })
    if set(copies) != installed_seen:
        raise ValueError("Orphaned installed contract not represented in dependency graph")
    edges.sort(key=lambda e: (e["consumer"], e["provider"], e["release"]))
    release_dependencies.sort(key=lambda e: (e["release"], e["depends_on"]))
    producer_local.sort(key=lambda e: (e["provider"], e["release"], e["copy"]))
    modules = sorted({e["consumer"] for e in edges} | {e["provider"] for e in edges})
    return {
        "schema_version": 1,
        "nodes": modules,
        "edges": edges,
        "release_dependencies": release_dependencies,
        "producer_local_copies": producer_local,
        "summary": {
            "producer_local_copies": len(producer_local),
            "declared_relationships": len(edges),
            "canonical_dependency_edges": len(release_dependencies),
            "with_installed_loader": sum(e["evidence"] == "installed-loader" for e in edges),
            "without_installed_loader": sum(e["evidence"] != "installed-loader" for e in edges),
            "by_kind": {name: sum(e["kind"] == name for e in edges)
                        for name in sorted(set(TYPE.values()))},
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    graph = derive()
    if args.output:
        rendered = json.dumps(graph, indent=2) + "\n"
        if args.check:
            if args.output.read_text() != rendered:
                raise ValueError("Derived contract dependency report is stale")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
    print(json.dumps(graph["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
