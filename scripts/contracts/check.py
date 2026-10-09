"""Validate named sources, schema IDs, current OpenAPI routes and consumer copies."""
from __future__ import annotations

import json
import re
from pathlib import Path
from build import verify

ROOT = Path(__file__).resolve().parents[2]

def load(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))

def unique_schema_ids():
    ids = {}
    for p in sorted((ROOT / "contracts/schemas").rglob("*.json")):
        item = json.loads(p.read_text(encoding="utf-8"))
        identifier = item.get("$id")
        if identifier:
            if identifier in ids:
                raise ValueError(f"Duplicate schema $id {identifier}: {ids[identifier]} and {p}")
            ids[identifier] = p
    return len(ids)

def local_refs(doc, label):
    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/"):
                current = doc
                for segment in ref[2:].split("/"):
                    key = segment.replace("~1", "/").replace("~0", "~")
                    if not isinstance(current, dict) or key not in current:
                        raise ValueError(f"Invalid {label} local $ref: {ref}")
                    current = current[key]
            for child in node.values():
                walk(child)
    walk(doc)

def current_api(name):
    doc = load(f"contracts/openapi/{name}")
    if doc.get("openapi") != "3.1.0":
        raise ValueError(f"Invalid OpenAPI dialect: {name}")
    ids = set()
    for path, item in doc["paths"].items():
        expected = set(re.findall(r"\\{([^}]+)\\}", path))
        for verb, op in item.items():
            if verb not in {"get", "post", "put", "patch", "delete"}:
                continue
            operation_id = op.get("operationId")
            if not operation_id or operation_id in ids:
                raise ValueError(f"Duplicate or missing operation ID: {name}:{path}")
            ids.add(operation_id)
            params = [*item.get("parameters", []), *op.get("parameters", [])]
            actual = {p["name"] for p in params if p.get("in") == "path"}
            if expected != actual or not op.get("responses"):
                raise ValueError(f"Invalid operation parameters/responses: {name}:{path}")
    local_refs(doc, name)
    return len(doc["paths"]), len(ids)

def check_routes():
    source = (ROOT / "services/planning/src/planning/interfaces/migration.py").read_text()
    match = re.search(r"\\(migration-preparations\\|migration-plans\\|[^()]+\\)", source)
    if match is None:
        raise ValueError("Cannot enumerate runtime migration routes")
    runtime = set(match.group()[1:-1].split("|"))
    actual = {p.rsplit("/", 1)[-1] for p in load("contracts/openapi/planning-migration-v1.6.json")["paths"]}
    if runtime != actual:
        raise ValueError(f"Runtime migration/OpenAPI path drift: {sorted(runtime ^ actual)}")

def check_copies():
    for source, destinations in {
        "contracts/openapi/catalogue-v1.0.1.json": ["apps/console/resources/contracts/catalogue-v1.0.1.json"],
        "contracts/schemas/planning/migration-support-v2.json": ["services/planning/src/planning/infrastructure/inputs/migration-support-v2.json"],
        "contracts/schemas/planning/migration-readiness-v2.json": ["services/planning/src/planning/infrastructure/inputs/migration-readiness-v2.json"],
    }.items():
        canonical = load(source)
        for destination in destinations:
            if load(destination) != canonical:
                raise ValueError(f"Packaged contract drift: {destination}")

def main():
    sources, bundles = verify()
    id_count = unique_schema_ids()
    paths, ops = 0, 0
    for name in ("catalogue-v1.0.1.json", "inventory-v1.8.json", "planning-migration-v1.6.json"):
        a, b = current_api(name)
        paths += a
        ops += b
    check_routes()
    check_copies()
    print(json.dumps(dict(status="PASS", sources=sources, bundles=bundles, unique_ids=id_count, paths=paths, operations=ops)))

if __name__ == "__main__":
    main()
