"""Validate named sources, schema IDs, current OpenAPI routes and consumer copies."""
from __future__ import annotations

import json
import re
import hashlib
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate_spec

from build import verify

ROOT = Path(__file__).resolve().parents[2]

def load(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))

def unique_schema_ids():
    """Never rewrite historical published schema bytes to repair old ID aliases.

    These *exact* three historical Inventory documents are archived: they shared
    an identifier before publication. A different file or changed byte fails.
    Only collection-page-v1.4 is active and has its own distinct schema $id.
    """
    old_id = "https://multi-tenant.invalid/contracts/inventory/collection-page-v1.1"
    historical = {
        "contracts/schemas/inventory/collection-page-v1.1.json":
            "9ae92e3af4b3a7cb96a00e721ce904d318263628",
        "contracts/schemas/inventory/collection-page-v1.2.json":
            "d9b9b241b29b5234a095a195476cc852041fe1dc",
        "contracts/schemas/inventory/collection-page-v1.3.json":
            "9f2d1c18bb26dee8072163853808d0504de4e828",
    }
    seen: dict[str, list[Path]] = {}
    for p in sorted((ROOT / "contracts/schemas").rglob("*.json")):
        item = json.loads(p.read_text(encoding="utf-8"))
        identifier = item.get("$id")
        if identifier:
            seen.setdefault(identifier, []).append(p)
    for identifier, paths in seen.items():
        if len(paths) <= 1:
            continue
        if identifier != old_id or {str(p.relative_to(ROOT)) for p in paths} != set(historical):
            raise ValueError(f"Unexpected duplicate schema $id {identifier}: {paths}")
        for p in paths:
            content = p.read_bytes()
            raw = b"blob " + str(len(content)).encode() + bytes([0]) + content
            digest = hashlib.sha1(raw).hexdigest()
            if digest != historical[str(p.relative_to(ROOT))]:
                raise ValueError(f"Historical schema was rewritten instead of versioned: {p}")
    return sum(len(paths) for paths in seen.values())


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

def check_routes():
    source = (ROOT / "services/planning/src/planning/interfaces/migration.py").read_text()
    match = re.search(r"\(migration-preparations\|migration-plans\|[^()]+\)", source)
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
        "contracts/schemas/planning/migration-readiness-v2.1.json": [
            "services/planning/src/planning/infrastructure/inputs/migration-readiness-v2.1.json",
            "services/lifecycle/src/lifecycle/infrastructure/contracts/migration-readiness-v2.1.json",
        ],
    }.items():
        canonical = (ROOT / source).read_bytes()
        for destination in destinations:
            if (ROOT / destination).read_bytes() != canonical:
                raise ValueError(f"Packaged contract byte drift: {destination}")

    # Historical canonical releases remain frozen, but these Console bundles
    # have no current runtime/generator/compatibility-script consumer.
    # Guard against accidentally reintroducing a stale duplicate copy.
    for retired in (
        "apps/console/resources/contracts/inventory-v1.7.json",
        "apps/console/resources/contracts/inventory-v1.8.json",
        "apps/console/resources/contracts/planning-migration-v1.4.json",
    ):
        if (ROOT / retired).exists():
            raise ValueError(f"Retired consumer contract copy reintroduced: {retired}")

def check_native_candidates():
    registry = load("contracts/capabilities/native-security-api-registry-v1.json")
    Draft202012Validator(
        load("contracts/schemas/capabilities/native-security-api-registry-v1.json"),
        format_checker=FormatChecker(),
    ).validate(registry)
    if registry["status"] != "candidate_paths_require_installed_qualification":
        raise ValueError("Native security API registry must never claim qualification")
    if set(registry["providers"]) != {"vmware", "ahv", "openstack"}:
        raise ValueError("Native security registry platform drift")
    for platform, provider in registry["providers"].items():
        if not provider["namespace"] or not provider["versions"]:
            raise ValueError(f"Missing candidate namespace or versions: {platform}")
        for version, record in provider["versions"].items():
            for name in ("required_features", "candidate_endpoints"):
                values = record[name]
                if not values or len(values) != len(set(values)):
                    raise ValueError(f"Invalid native candidate feature/endpoints: {platform}/{version}")
            if any(not endpoint.startswith("/") for endpoint in record["candidate_endpoints"]):
                raise ValueError(f"Invalid native endpoint path: {platform}/{version}")
    for platform in ("ahv", "openstack"):
        projection = load(f"contracts/platforms/{platform}/source-profile-v1.json")
        Draft202012Validator(
            load("contracts/schemas/platforms/source-profile-v1.json"),
            format_checker=FormatChecker(),
        ).validate(projection)
        fields = ["vm"] if platform == "ahv" else ["server", "volume"]
        if projection["schema_version"] != 1:
            raise ValueError(f"Invalid {platform} source profile")
        for field in fields:
            values = projection[field]
            if not values or len(set(values)) != len(values):
                raise ValueError(f"Duplicate/missing native profile field: {platform}/{field}")


def check_events():
    """Parse complete AsyncAPI 3 contracts and resolve their event payloads."""
    base = ROOT / "contracts/asyncapi"
    for path in sorted(base.glob("*.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or document.get("asyncapi") != "3.0.0":
            raise ValueError(f"Invalid AsyncAPI release: {path}")
        if not document.get("channels") or not document.get("operations"):
            raise ValueError(f"Missing AsyncAPI channels or operations: {path}")
        local_refs(document, str(path))
        messages = document.get("components", {}).get("messages", {})
        if not messages:
            raise ValueError(f"Missing AsyncAPI message definitions: {path}")
        for message_name, message in messages.items():
            if message.get("contentType") != "application/json":
                raise ValueError(f"Invalid event media type: {path}:{message_name}")
            payload = message.get("payload", {})
            if payload.get("schemaFormat") != (
                "application/schema+json;version=draft-2020-12"
            ):
                raise ValueError(f"Invalid event schema format: {path}:{message_name}")
            reference = payload.get("schema", {}).get("$ref")
            if not isinstance(reference, str) or not reference.startswith(
                "../schemas/events/"
            ):
                raise ValueError(f"Missing event schema reference: {path}:{message_name}")
            event = (path.parent / reference).resolve()
            if not event.is_relative_to((ROOT / "contracts/schemas/events").resolve()):
                raise ValueError(f"Unsafe event schema reference: {path}:{reference}")
            if not event.is_file():
                raise ValueError(f"Unresolved AsyncAPI event schema: {path}:{reference}")
            schema = json.loads(event.read_text(encoding="utf-8"))
            if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                raise ValueError(f"Wrong event JSON Schema dialect: {event}")
            Draft202012Validator.check_schema(schema)


def check_schema_dialects():
    """Fail on malformed published JSON Schemas, beyond duplicate-id checks."""
    found = 0
    for path in sorted((ROOT / "contracts/schemas").rglob("*.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise ValueError(f"Unsupported JSON Schema dialect: {path}")
        Draft202012Validator.check_schema(schema)
        found += 1
    return found


def check_readiness_projection():
    """Wire v2 must be the authoritative embedded OpenAPI component.

    The installed v2.1 validation profile may be stricter, without changing
    the published wire v2 semantics or rewriting Planning v1.6 API bytes.
    """
    from generate_readiness import embedded_payload

    expected = embedded_payload()
    api = load("contracts/openapi/planning-migration-v1.6.json")
    fragment = load(
        "contracts/source/openapi/planning-migration-v1.6/"
        "components-schemas/workload-readiness.json"
    )
    if (api["components"]["schemas"]["MigrationReadinessPayload"] != expected
            or fragment["MigrationReadinessPayload"] != expected):
        raise ValueError("Planning OpenAPI and canonical readiness-v2 projection drift")


def check_consumer_registry():
    registry = load("architecture/contract-consumers.json")
    inventory = registry["contracts"]
    for source, consumers in {
        "contracts/openapi/catalogue-v1.0.1.json": {"catalogue", "console"},
        "contracts/openapi/inventory-v1.9.json": {"inventory", "console"},
        "contracts/openapi/planning-migration-v1.6.json": {"planning", "console"},
        "contracts/schemas/planning/migration-input-v4.json": {"inventory", "planning"},
    }.items():
        if source not in inventory:
            raise ValueError(f"Active contract missing from consumer registry: {source}")
        if not consumers.issubset(set(inventory[source])):
            raise ValueError(f"Incorrect active consumer registry: {source}")
    releases = registry.get("active_releases")
    if not isinstance(releases, list) or len(releases) < 6:
        raise ValueError("Missing machine-readable active contract release catalogue")
    names = [entry["path"] for entry in releases]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate active contract release")
    for entry in releases:
        path = entry["path"]
        owner = entry["owner"]
        consumers = entry["consumers"]
        if (not (ROOT / path).is_file()
                or owner not in registry["dependencies"]
                or not consumers
                or set(consumers) - set(registry["dependencies"])):
            raise ValueError(f"Invalid active release ownership or consumers: {path}")
        if not {owner, *consumers}.issubset(set(inventory.get(path, []))):
            raise ValueError(f"Undeclared active release consumer: {path}")
        for dependency in entry.get("depends_on", []):
            if not (ROOT / dependency).is_file():
                raise ValueError(f"Unresolved active contract dependency: {dependency}")
        manifest = entry.get("source_manifest")
        if manifest:
            source = load(manifest)
            if source.get("target") != path:
                raise ValueError(f"Active contract source manifest drift: {path}")
        for installed in entry.get("copies", []):
            if (ROOT / installed).read_bytes() != (ROOT / path).read_bytes():
                raise ValueError(f"Active contract installed-copy drift: {installed}")


def main():
    sources, bundles = verify()
    id_count = unique_schema_ids()
    schema_count = check_schema_dialects()
    paths, ops = 0, 0
    for name in ("catalogue-v1.0.1.json", "inventory-v1.9.json", "planning-migration-v1.6.json"):
        a, b = current_api(name)
        paths += a
        ops += b
    check_routes()
    check_copies()
    check_native_candidates()
    check_events()
    check_readiness_projection()
    check_consumer_registry()
    print(json.dumps(dict(status="PASS", sources=sources, bundles=bundles, unique_ids=id_count, schema_count=schema_count, paths=paths, operations=ops)))

if __name__ == "__main__":
    main()
