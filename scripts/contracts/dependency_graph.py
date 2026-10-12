"""Derive contract change-impact edges from active releases and installed consumers.

Do not infer service call direction from the legacy architectural layering DAG:
wire, event, shared schema, capability and platform profile dependencies are
different relationships and may legitimately form cycles.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TYPE = {
    "openapi": "http",
    "asyncapi": "event",
    "schemas": "schema",
    "capabilities": "capability",
    "platforms": "platform",
}


def derive(root: Path = ROOT) -> dict:
    registry = json.loads((root / "architecture/contract-consumers.json").read_text())
    usage = json.loads((root / "architecture/installed-contract-usage.json").read_text())
    copies = {item["copy"]: item for item in usage["copies"]}
    edges = []
    producer_local = []
    installed_seen = set()
    for entry in registry["active_releases"]:
        canonical, owner = entry["path"], entry["owner"]
        kind = canonical.split("/")[1]
        if kind not in TYPE:
            raise ValueError(f"Unknown active contract classification: {canonical}")
        if not (root / canonical).is_file():
            raise ValueError(f"Missing active dependency source: {canonical}")
        declared_consumers = entry["consumers"]
        if len(declared_consumers) != len(set(declared_consumers)):
            raise ValueError(f"Duplicate consumers on: {canonical}")
        bindings = {}
        for copy in entry.get("copies", []):
            if copy not in copies or copies[copy]["canonical"] != canonical:
                raise ValueError(f"Unknown installed dependency: {copy}")
            component = "/".join(Path(copy).parts[:2])
            consumer = ("console" if component == "apps/console"
                        else component.split("/")[1])
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
    producer_local.sort(key=lambda e: (e["provider"], e["release"], e["copy"]))
    modules = sorted({e["consumer"] for e in edges} | {e["provider"] for e in edges})
    return {
        "schema_version": 1,
        "nodes": modules,
        "edges": edges,
        "producer_local_copies": producer_local,
        "summary": {
            "producer_local_copies": len(producer_local),
            "declared_relationships": len(edges),
            "with_installed_loader": sum(e["evidence"] == "installed-loader" for e in edges),
            "without_installed_loader": sum(e["evidence"] != "installed-loader" for e in edges),
            "by_kind": {name: sum(e["kind"] == name for e in edges)
                        for name in sorted(set(TYPE.values()))},
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    graph = derive()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(graph["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
