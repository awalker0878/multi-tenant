"""Canonical OpenAPI, schema identities, source parity, and route declarations."""
from __future__ import annotations
import json
import re
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate_spec
ROOT = Path(__file__).resolve().parents[2]

def load(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def unique_schema_ids():
    """Every retained schema has a unique identifier; no historical exceptions."""
    seen: dict[str, Path] = {}
    for path in sorted((ROOT / "contracts/schemas").rglob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        identifier = document.get("$id")
        if not identifier:
            continue
        if identifier in seen:
            raise ValueError(f"Duplicate schema $id {identifier}: {seen[identifier]} and {path}")
        seen[identifier] = path
    return len(seen)


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
    if doc.get("openapi") not in {"3.1.0", "3.0.4"}:
        raise ValueError(f"Invalid OpenAPI dialect: {name}")
    ids = set()
    for path, item in doc["paths"].items():
        expected = set(re.findall(r"\{([^}]+)\}", path))
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
    validate_spec(doc)
    return len(doc["paths"]), len(ids)


def check_schema_dialects():
    """Validate all current schema releases; document the few pre-ID active formats."""
    active_without_id = {
        "capabilities/migration-collection-manifest-v1.json",
        "capabilities/migration-feature-policy-v1.json",
        "capabilities/migration-field-crosswalk-v1.json",
        "events/catalogue-intent-v1.json",
        "planning/catalogue-input-v1.json",
        "planning/fact-v1.json",
        "planning/inventory-input-v1.json",
        "planning/inventory-input-v2.json",
    }
    found = 0
    for path in sorted((ROOT / "contracts/schemas").rglob("*.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        relative = str(path.relative_to(ROOT / "contracts/schemas"))
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise ValueError(f"Unsupported JSON Schema dialect: {path}")
        identifier = schema.get("$id")
        if (identifier is None) != (relative in active_without_id):
            raise ValueError(f"Schema identity required for this active release: {path}")
        if identifier is not None and (
            not isinstance(identifier, str) or not identifier.strip()
        ):
            raise ValueError(f"Invalid published schema identifier: {path}")
        Draft202012Validator.check_schema(schema)
        local_refs(schema, str(path))
        found += 1
    return found


def check_readiness_projection():
    """Wire v2 must be the authoritative embedded OpenAPI component.

    The installed v2.2 validation profile may be stricter, without changing
    the published wire v2 semantics or rewriting Planning v1.6 API bytes.
    """
    from generate_readiness import embedded_payload

    expected = embedded_payload()
    api = load("contracts/openapi/planning-migration-v2.json")
    fragment = load(
        "contracts/source/openapi/planning-migration-v2/"
        "components-schemas/workload-readiness.json"
    )
    if (api["components"]["schemas"]["MigrationReadinessPayload"] != expected
            or fragment["MigrationReadinessPayload"] != expected):
        raise ValueError("Planning OpenAPI and canonical readiness-v2 projection drift")
