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
from runtime_inventory import verify_runtime_inventory

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
        "contracts/schemas/planning/migration-readiness-v2.2.json": [
            "services/planning/src/planning/infrastructure/inputs/migration-readiness-v2.2.json",
            "services/lifecycle/src/lifecycle/infrastructure/contracts/migration-readiness-v2.2.json",
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


def event_discriminator(schema: dict, address: str, document_name: str) -> dict:
    """A channel-specific *validation profile*, never a mutation of published v1.

    Some Catalogue intent facts deliberately multiplex four types on one channel.
    Other channels must be bound to one event_type derived from their address.
    """
    value = schema.get("properties", {}).get("event_type", {})
    names = set(value.get("enum", [value["const"]] if "const" in value else []))
    expected = address.removesuffix(".v1")
    if expected in names:
        admitted = {expected}
    elif document_name == "catalogue-intent.yaml" and address == "catalogue.intent.changed.v1":
        admitted = names
    else:
        raise ValueError(f"AsyncAPI channel has no event_type binding: {document_name}:{address}")
    if not admitted:
        raise ValueError(f"Empty event discriminator: {document_name}:{address}")
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "allOf": [schema, {
            "type": "object", "required": ["event_type"],
            "properties": {"event_type": {"enum": sorted(admitted)}},
        }],
    }


def check_events():
    """Validate broker address, operation, schema and channel-specific type bindings."""
    base = ROOT / "contracts/asyncapi"
    all_addresses: dict[str, str] = {}
    for path in sorted(base.glob("*.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or document.get("asyncapi") != "3.0.0":
            raise ValueError(f"Invalid AsyncAPI release: {path}")
        if not document.get("channels") or not document.get("operations"):
            raise ValueError(f"Missing AsyncAPI channels or operations: {path}")
        local_refs(document, str(path))
        channels, operations = document["channels"], document["operations"]
        if not isinstance(channels, dict) or not isinstance(operations, dict):
            raise ValueError(f"Invalid AsyncAPI channel/operation maps: {path}")
        messages = document.get("components", {}).get("messages", {})
        if not isinstance(messages, dict) or not messages:
            raise ValueError(f"Missing AsyncAPI messages: {path}")
        used: set[str] = set()
        grouped: dict[str, set[str]] = {}
        schemas: dict[str, dict] = {}
        for name, message in messages.items():
            if not isinstance(message, dict) or message.get("contentType") != "application/json":
                raise ValueError(f"Invalid event message media type: {path}:{name}")
            payload = message.get("payload", {})
            if not isinstance(payload, dict) or payload.get("schemaFormat") != (
                "application/schema+json;version=draft-2020-12"
            ):
                raise ValueError(f"Invalid event schema format: {path}:{name}")
            reference = payload.get("schema", {}).get("$ref")
            if not isinstance(reference, str) or not reference.startswith("../schemas/events/"):
                raise ValueError(f"Missing event schema reference: {path}:{name}")
            event = (path.parent / reference).resolve()
            if (not event.is_relative_to((ROOT / "contracts/schemas/events").resolve())
                    or not event.is_file()):
                raise ValueError(f"Unsafe/unresolved event schema reference: {path}:{reference}")
            schema = json.loads(event.read_text(encoding="utf-8"))
            if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                raise ValueError(f"Wrong event JSON Schema dialect: {event}")
            Draft202012Validator.check_schema(schema)
            schemas[name] = schema
            grouped[name] = set()
        for key, channel in channels.items():
            if not isinstance(channel, dict):
                raise ValueError(f"Invalid AsyncAPI channel: {path}:{key}")
            address = channel.get("address")
            if not isinstance(address, str) or not address:
                raise ValueError(f"Invalid AsyncAPI channel address: {path}:{key}")
            if address in all_addresses:
                raise ValueError(f"Duplicate AsyncAPI address across releases: {address}")
            all_addresses[address] = str(path)
            bindings = channel.get("messages")
            if not isinstance(bindings, dict) or not bindings:
                raise ValueError(f"Missing AsyncAPI channel messages: {path}:{key}")
            for ref in bindings.values():
                name_ref = ref.get("$ref") if isinstance(ref, dict) else None
                if (not isinstance(name_ref, str) or
                        not name_ref.startswith("#/components/messages/")):
                    raise ValueError(f"Invalid channel message binding: {path}:{key}")
                name = name_ref.removeprefix("#/components/messages/")
                if name not in schemas:
                    raise ValueError(f"Unresolved channel message: {path}:{key}:{name}")
                profile = event_discriminator(schemas[name], address, path.name)
                Draft202012Validator.check_schema(profile)
                grouped[name].update(profile["allOf"][1]["properties"]["event_type"]["enum"])
                used.add(name)
        for name, schema in schemas.items():
            if name not in used:
                raise ValueError(f"Unused AsyncAPI message: {path}:{name}")
            prop = schema.get("properties", {}).get("event_type", {})
            all_types = set(prop.get("enum", [prop["const"]] if "const" in prop else []))
            if grouped[name] != all_types:
                raise ValueError(f"Unrouted event types: {path}:{name}:{sorted(all_types - grouped[name])}")
        covered: set[str] = set()
        for name, operation in operations.items():
            if (not isinstance(operation, dict) or operation.get("action") not in {"send", "receive"}
                    or not isinstance(operation.get("channel"), dict)
                    or operation["channel"].get("$ref") not in {
                        "#/channels/" + key for key in channels
                    }):
                raise ValueError(f"Unbound AsyncAPI operation: {path}:{name}")
            covered.add(operation["channel"]["$ref"].removeprefix("#/channels/"))
        if covered != set(channels):
            raise ValueError(f"AsyncAPI channels without operations: {path}:{sorted(set(channels) - covered)}")


def check_schema_dialects():
    """Validate every schema; only explicitly archived v1 releases may omit $id."""
    archival_without_id = {
        "capabilities/api-version-record-v1.json",
        "capabilities/migration-collection-manifest-v1.json",
        "capabilities/migration-feature-policy-v1.json",
        "capabilities/migration-field-crosswalk-v1.json",
        "events/catalogue-intent-v1.json",
        "planning/admission-record-v1.json",
        "planning/catalogue-input-v1.json",
        "planning/content-v1.json",
        "planning/fact-v1.json",
        "planning/inventory-input-v1.json",
        "planning/inventory-input-v2.json",
        "planning/migration-input-v1.json",
        "planning/migration-input-v2.json",
        "planning/migration-input-v3.json",
        "planning/migration-support-v1.json",
        "planning/qualification-v1.json",
        "planning/reservation-receipt-v1.json",
    }
    found = 0
    for path in sorted((ROOT / "contracts/schemas").rglob("*.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        relative = str(path.relative_to(ROOT / "contracts/schemas"))
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise ValueError(f"Unsupported JSON Schema dialect: {path}")
        identifier = schema.get("$id")
        if (identifier is None) != (relative in archival_without_id):
            raise ValueError(f"Schema identity required or archival exception changed: {path}")
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
    if set(names) != set(inventory):
        raise ValueError("Active contract registry does not cover every declared consumer")
    if len(names) != len(set(names)):
        raise ValueError("Duplicate active contract release")
    for entry in releases:
        path = entry["path"]
        owner = entry["owner"]
        consumers = entry["consumers"]
        if (not (ROOT / path).is_file()
                or owner not in registry["dependencies"]
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
    verify_runtime_inventory(registry, ROOT)


def main():
    sources, bundles = verify()
    id_count = unique_schema_ids()
    schema_count = check_schema_dialects()
    paths, ops = 0, 0
    active = load("architecture/contract-consumers.json")["active_releases"]
    apis = sorted(entry["path"].rsplit("/", 1)[-1] for entry in active
                  if entry["path"].startswith("contracts/openapi/"))
    for name in apis:
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
