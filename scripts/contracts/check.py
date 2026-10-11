"""Validate named sources, schema IDs, current OpenAPI routes and consumer copies."""
from __future__ import annotations

import json
import re
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
        "contracts/openapi/assurance-evidence-v1.json": {"assurance"},
        "contracts/openapi/inventory-native-input-v1.3.json": {"inventory", "planning", "lifecycle"},
        "contracts/openapi/catalogue-internal-v1.json": {"catalogue", "planning", "lifecycle"},
        "contracts/openapi/governance-service-checks-v1.json": {"governance", "planning"},
        "contracts/openapi/governance-inventory-collection-v1.1.json": {"governance", "inventory"},
        "contracts/openapi/governance-native-approval-v1.1.json": {"governance", "lifecycle"},
        "contracts/openapi/assurance-qualification-v1.json": {"assurance", "planning"},
        "contracts/schemas/common/error-v1.json": {"contract-platform", "inventory", "governance", "catalogue", "assurance"},
        "contracts/openapi/lifecycle-migration-boundary-v2.json": {"lifecycle", "lifecycle-workers"},
        "contracts/openapi/planning-immutable-plan-v1.1.json": {"planning", "governance"},
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
    # Each live service operation belongs to exactly one active versioned owner
    # release. Historical superseded bundles stay in the tree but are not active.
    seen_operations = {}
    for entry in releases:
        if not entry["path"].startswith("contracts/openapi/"):
            continue
        api = load(entry["path"])
        for endpoint, methods in api["paths"].items():
            for method in methods:
                if method not in {"get", "post", "put", "patch", "delete"}:
                    continue
                operation = (entry["owner"], method.upper(), endpoint)
                if operation in seen_operations:
                    raise ValueError(f"Overlapping active owner operation: {operation} in {seen_operations[operation]} and {entry['path']}")
                seen_operations[operation] = entry["path"]
    # The deployed broker definitions are all implemented products, not optional
    # self-declared inventory entries. Their schema dependencies must be active.
    # This detects removal of an event spec from both editable registry maps.
    for event_api in sorted((ROOT / "contracts/asyncapi").glob("*.yaml")):
        api_path = str(event_api.relative_to(ROOT))
        if api_path not in names:
            raise ValueError(f"Deployed AsyncAPI missing from active releases: {api_path}")
        doc = yaml.safe_load(event_api.read_text(encoding="utf-8"))
        for message in doc.get("components", {}).get("messages", {}).values():
            reference = message["payload"]["schema"]["$ref"]
            schema_path = str((event_api.parent / reference).resolve().relative_to(ROOT.resolve()))
            if schema_path not in names:
                raise ValueError(f"Event payload schema missing from active releases: {schema_path}")
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



def check_owner_operation_bindings():
    """Enforce actual Planning owner-operation bindings independently of the registry.

    This closes the loophole where the executable owner selects a JSON file via
    importlib.resources dynamically and literal filename scanning sees nothing.
    """
    import runpy

    module = ROOT / "services/planning/src/planning/infrastructure/owner_contracts.py"
    operations = runpy.run_path(str(module))["OWNER_OPERATIONS"]
    registry = load("architecture/contract-consumers.json")
    releases = {entry["path"]: entry for entry in registry["active_releases"]}
    required = {
        ("CATALOGUE", "catalogue-input-v1"),
        ("CATALOGUE", "catalogue-current-v2"),
        ("INVENTORY", "inventory-input-v2"),
        ("INVENTORY", "migration-input-v4"),
        ("ASSURANCE", "qualification-v2.1"),
        ("ASSURANCE", "migration-support-v2"),
    }
    present = set()
    for owner, method, pattern, schema in operations:
        if owner not in {"CATALOGUE", "INVENTORY", "ASSURANCE"} or method not in {"GET", "POST"}:
            raise ValueError(f"Invalid owner operation: {owner}:{method}:{schema}")
        re.compile(pattern)
        present.add((owner, schema))
        canonical = f"contracts/schemas/planning/{schema}.json"
        installed = f"services/planning/src/planning/infrastructure/inputs/{schema}.json"
        item = releases.get(canonical)
        if (item is None or installed not in item.get("copies", [])
                or "planning" not in item.get("consumers", [])
                or item["owner"] != owner.lower()):
            raise ValueError(f"Runtime owner-operation contract missing from registry: {canonical}")
        if not (ROOT / installed).is_file() or (ROOT / canonical).read_bytes() != (ROOT / installed).read_bytes():
            raise ValueError(f"Runtime owner-operation schema drift: {installed}")
    if present != required:
        raise ValueError(f"Owner operation binding incomplete: {sorted(required - present)}")
    # The deployed current-intent v2 schema includes the exact published Intent
    # definition, rather than a loose top-level object with untyped subtrees.
    current = load("contracts/schemas/planning/catalogue-current-v2.json")
    original = load("contracts/schemas/planning/catalogue-input-v1.json")
    published = load("contracts/schemas/catalogue/intent-v1.json")
    projected = current.get("$defs", {}).get("Intent")
    source = original["components"]["schemas"]["Intent"]
    keys = ("type", "additionalProperties", "properties", "required")
    if (projected != source or
            any(source.get(key) != published.get(key) for key in keys)):
        raise ValueError("Current Catalogue intent projection differs from its canonical source")
    Draft202012Validator.check_schema(current)




def check_implemented_api_contracts():
    """Independent required-operation canaries: removing both registry maps fails."""
    release_by_path = {
        entry["path"]: entry
        for entry in load("architecture/contract-consumers.json")["active_releases"]
    }
    required = {
        "contracts/openapi/assurance-evidence-v1.json": (
            "assurance",
            {
                ("POST", "/v1/tenants/{tenant}/evidence-uploads"),
                ("POST", "/v1/tenants/{tenant}/evidence-uploads/{evidence}/finalization"),
                ("GET", "/v1/tenants/{tenant}/evidence/{evidence}"),
                ("POST", "/v1/tenants/{tenant}/evidence/{evidence}/reviews"),
            },
        ),
        "contracts/openapi/catalogue-internal-v1.json": (
            "catalogue", {
                ("GET", "/v1/tenants/{tenant}/planning-inputs/{application}/{environment}/{site}/{revision}"),
                ("GET", "/internal/tenants/{tenant}/applications/{application}/environments/{environment}/current-planning-intent"),
            },
        ),
        "contracts/openapi/planning-native-v1.json": (
            "planning", {("POST", "/v1/tenants/{tenant}/applications/{application}/environments/{environment}/native-plans")},
        ),
        "contracts/openapi/planning-qualification-events-v1.json": (
            "planning", {("POST", "/internal/qualification-events")},
        ),
        "contracts/openapi/lifecycle-internal-authority-v1.json": (
            "lifecycle", {
                *{("POST", "/internal/tenants/{tenant}/placement-reservations/" + command)
                  for command in ("reserve", "checks", "confirm", "renew", "release")},
                ("GET", "/internal/evidence-bindings/{tenant}/{job}"),
                ("POST", "/internal/simulation-grants/redemptions"),
            },
        ),
        "contracts/openapi/inventory-collection-worker-v1.json": (
            "inventory", {
                ("POST", "/internal/collections/claim"),
                ("POST", "/internal/collections/pages"),
                ("POST", "/internal/collections/profile-reads"),
                ("POST", "/internal/collections/receipts"),
            },
        ),
        "contracts/openapi/inventory-native-input-v1.3.json": (
            "inventory", {
                ( "GET", f"/{prefix}/tenants/{{tenant}}/{resource}/{{application}}/{{environment}}/{{site}}/{suffix}")
                for prefix in ("internal", "v1")
                for resource, suffix in (
                    ("migration-inputs", "{revision}/{digest}"),
                    ("planning-inputs", "{endpoint}/{generation}"),
                    ("planning-capability-inputs", "{endpoint}/{generation}"),
                ) if not (prefix == "internal" and resource == "planning-inputs")
            },
        ),
        "contracts/openapi/governance-inventory-collection-v1.1.json": (
            "governance", {("POST", "/v1/tenants/{tenant}/inventory-collection-checks")},
        ),
        "contracts/openapi/governance-native-approval-v1.1.json": (
            "governance", {("POST", "/v1/tenants/{tenant}/native-approval-checks")},
        ),
        "contracts/openapi/governance-service-checks-v1.json": (
            "governance", {
                ("POST", "/v1/tenants/{tenant}/planning-input-checks"),
                ("POST", "/v1/tenants/{tenant}/execution-approval-checks"),
            },
        ),
        "contracts/openapi/assurance-qualification-v1.json": (
            "assurance", {
                ("POST", "/v1/tenants/{tenant}/migration-qualifications"),
                ("POST", "/internal/tenants/{tenant}/qualification-checks"),
                ("POST", "/internal/tenants/{tenant}/qualification-publications"),
                ("POST", "/v1/tenants/{tenant}/planning-qualification-v2"),
            },
        ),
        "contracts/openapi/lifecycle-migration-boundary-v2.json": (
            "lifecycle",
            {("POST", "/internal/native-grants/checks")},
        ),
        "contracts/openapi/planning-immutable-plan-v1.1.json": (
            "planning",
            {("GET", "/v1/plans/{plan}/revisions/{revision}")},
        ),
        "contracts/openapi/planning-lifecycle-reads-v1.json": (
            "planning",
            {
                ("GET", "/v1/tenants/{tenant}/execution-plans/{plan}/revisions/{revision}"),
                ("GET", "/internal/tenants/{tenant}/placement-proposals/{plan}/revisions/{revision}"),
            },
        ),
    }
    for path, (owner, operations) in required.items():
        release = release_by_path.get(path)
        if release is None or release["owner"] != owner:
            raise ValueError(f"Implemented OpenAPI release not registered: {path}")
        document = load(path)
        actual = {
            (verb.upper(), endpoint)
            for endpoint, item in document["paths"].items()
            for verb in item if verb in {"get", "post", "put", "patch", "delete"}
        }
        if actual != operations:
            raise ValueError(f"Implemented OpenAPI operation drift: {path} {sorted(actual ^ operations)}")

    # Independent emitted-status expectations for the freshly versioned
    # Governance admission boundaries. Controller/HTTP fixture tests must still
    # independently exercise each branch before CI can be called exhaustive.
    for path, expected in {
        "contracts/openapi/governance-inventory-collection-v1.1.json": {"200", "401", "403", "422", "503"},
        "contracts/openapi/governance-native-approval-v1.1.json": {"200", "401", "403", "404", "409", "422", "503"},
    }.items():
        release = load(path)
        result = next(iter(release["paths"].values()))["post"]["responses"]
        if set(result) != expected:
            raise ValueError(f"Governance authority status drift: {path} {sorted(set(result) ^ expected)}")

    # Assert headers that convey delegated actor and requested action. Bearer
    # authentication alone is not a sufficient authority contract.
    actor_headers = {
        ("contracts/openapi/governance-service-checks-v1.json",
         "/v1/tenants/{tenant}/planning-input-checks"): ("X-Actor-Delegation",),
        ("contracts/openapi/catalogue-internal-v1.json",
         "/v1/tenants/{tenant}/planning-inputs/{application}/{environment}/{site}/{revision}"):
            ("X-Actor-Delegation", "X-Planning-Action"),
        ("contracts/openapi/assurance-qualification-v1.json",
         "/v1/tenants/{tenant}/planning-qualification-v2"):
            ("X-Actor-Delegation", "X-Planning-Action"),
    }
    for path in load("contracts/openapi/inventory-native-input-v1.3.json")["paths"]:
        if path.startswith("/v1/"):
            actor_headers[("contracts/openapi/inventory-native-input-v1.3.json", path)] = (
                "X-Actor-Delegation", "X-Planning-Action")
    for (release, endpoint), required in actor_headers.items():
        operation = next(op for verb, op in load(release)["paths"][endpoint].items()
                         if verb in {"get", "post"})
        actual = {p["name"]: p for p in operation["parameters"] if p["in"] == "header"}
        if any(name not in actual or actual[name].get("required") is not True for name in required):
            raise ValueError(f"Missing delegated authority header contract: {release} {endpoint}")
    for release, endpoint in (
        ("contracts/openapi/governance-native-approval-v1.1.json",
         "/v1/tenants/{tenant}/native-approval-checks"),
        ("contracts/openapi/governance-service-checks-v1.json",
         "/v1/tenants/{tenant}/execution-approval-checks"),
    ):
        if "409" not in load(release)["paths"][endpoint]["post"]["responses"]:
            raise ValueError(f"Missing Governance bound-plan digest conflict: {release}")

    # The independent Inventory producer and packaged Planning consumer both
    # serve the canonical v4 envelope; a copy mismatch must fail even if the
    # active registry and OpenAPI document are edited together.
    api = load("contracts/openapi/inventory-native-input-v1.3.json")
    endpoint = "/internal/tenants/{tenant}/migration-inputs/{application}/{environment}/{site}/{revision}/{digest}"
    response = api["components"]["schemas"]["MigrationInput"]
    canonical = load("contracts/schemas/planning/migration-input-v4.json")
    installed = load("services/planning/src/planning/infrastructure/inputs/migration-input-v4.json")
    if response != canonical or canonical != installed:
        raise ValueError("Inventory native-input v1.3 producer/consumer v4 schema mismatch")
    for prefix in ("internal", "v1"):
        endpoint = f"/{prefix}/tenants/{{tenant}}/migration-inputs/{{application}}/{{environment}}/{{site}}/{{revision}}/{{digest}}"
        if api["paths"][endpoint]["get"]["responses"]["200"]["content"]["application/json"]["schema"] != {"$ref": "#/components/schemas/MigrationInput"}:
            raise ValueError(f"Inventory v1.3 migration schema reference drift: {endpoint}")
    Draft202012Validator.check_schema(response)

    # A schema embedded into OpenAPI must have its local definitions rebased.
    # Only the reference anchor changes; the active Catalogue v2 payload is
    # otherwise an exact projection of the canonical producer schema.
    embedded = load("contracts/openapi/catalogue-internal-v1.json")["components"]["schemas"]["CurrentPlanningIntent"]
    current = load("contracts/schemas/planning/catalogue-current-v2.json")
    def relocate_current(node):
        if isinstance(node, list):
            for item in node:
                relocate_current(item)
        elif isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                node["$ref"] = ref.replace("#/$defs/", "#/components/schemas/CurrentPlanningIntent/$defs/", 1)
            for item in node.values():
                relocate_current(item)
    relocate_current(current)
    if embedded != current:
        raise ValueError("Catalogue current-v2 OpenAPI projection drift")

    # Canonical producer -> active OpenAPI -> installed consumer parity.
    # No release-specific reimplementation of a payload schema is authoritative.
    # New HTTP releases constrain UUID syntax without changing source field sets.
    def normalize_uuids(node):
        if isinstance(node, list):
            return [normalize_uuids(item) for item in node]
        if isinstance(node, dict):
            result = {key: normalize_uuids(value) for key, value in node.items()}
            if result.get("format") == "uuid":
                result["pattern"] = UUID_PATTERN
            return result
        return node

    inv_api = load("contracts/openapi/inventory-native-input-v1.3.json")
    for embedded, source, installed in (
        ("PlanningInput", "contracts/schemas/planning/inventory-input-v1.json",
         "services/planning/src/planning/infrastructure/inputs/inventory-input-v1.json"),
        ("CapabilityInput", "contracts/schemas/planning/inventory-input-v2.json",
         "services/planning/src/planning/infrastructure/inputs/inventory-input-v2.json"),
    ):
        reference = normalize_uuids(load(source))
        if inv_api["components"]["schemas"][embedded] != reference or load(source) != load(installed):
            raise ValueError(f"Inventory native {embedded} producer/consumer schema drift")
    assurance_api = load("contracts/openapi/assurance-qualification-v1.json")
    for embedded, source in (
        ("Qualification", "contracts/schemas/planning/qualification-v2.1.json"),
        ("MigrationSupport", "contracts/schemas/planning/migration-support-v2.json"),
    ):
        if assurance_api["components"]["schemas"][embedded] != normalize_uuids(load(source)):
            raise ValueError(f"Assurance {embedded} canonical response schema drift")
    catalogue_api = load("contracts/openapi/catalogue-internal-v1.json")
    catalogue_input = normalize_uuids(load("contracts/schemas/planning/catalogue-input-v1.json"))
    catalogue_input.pop("components", None)  # Source also carries standalone OpenAPI components.
    if catalogue_api["components"]["schemas"]["PlanningInput"] != catalogue_input:
        raise ValueError("Catalogue PlanningInput canonical response schema drift")

    # Internal Lifecycle reads derive their immutable binding and base content
    # from published Planning v1.2. The embedded readiness contract is a
    # relocation of v2.2 with only its local JSON references re-anchored.
    api = load("contracts/openapi/planning-lifecycle-reads-v1.json")
    schemas = api["components"]["schemas"]
    published = load("contracts/openapi/planning-v1.2.json")["components"]["schemas"]
    if schemas["BoundPlan"] != published["BoundPlan"]:
        raise ValueError("Planning Lifecycle binding differs from canonical Planning binding")
    baseline = published["Content"]
    current = schemas["Content"]
    if current.get("required") != baseline.get("required") or any(
        current["properties"].get(key) != value
        for key, value in baseline["properties"].items()
    ):
        raise ValueError("Planning Lifecycle content differs from canonical Planning content")
    optional = set(current["properties"]) - set(baseline["properties"])
    if optional != {"native_provisioning", "native_migration", "migration_campaign"}:
        raise ValueError("Planning Lifecycle content extension list drift")
    expected = load("contracts/schemas/planning/migration-readiness-v2.2.json")
    expected.pop("$schema", None)
    expected.pop("$id", None)
    def relocate(node):
        if isinstance(node, list):
            for value in node:
                relocate(value)
        elif isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                node["$ref"] = ref.replace(
                    "#/$defs/", "#/components/schemas/MigrationReadiness/$defs/", 1
                )
            for value in node.values():
                relocate(value)
    relocate(expected)
    if schemas["MigrationReadiness"] != expected:
        raise ValueError("Planning Lifecycle embedded migration readiness differs from v2.2")



UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
UUID_V4_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"


def check_uuid_policy():
    """Enforce current authority-release identifiers without historical exceptions.

    Published historical bundles are immutable and are not retroactively
    reinterpreted or validated through a legacy compatibility allowlist.
    Every newly owned authority release must be added here; a versioned
    release requires independent registration and an explicit conformance test.
    """
    releases = (
        "catalogue-internal-v1.json",
        "inventory-native-input-v1.3.json",
        "inventory-collection-worker-v1.json",
        "planning-qualification-events-v1.json",
        "lifecycle-internal-authority-v1.json",
        "governance-service-checks-v1.json",
        "assurance-qualification-v1.json",
        "governance-inventory-collection-v1.1.json",
        "governance-native-approval-v1.1.json",
    )
    canonical = load("contracts/schemas/planning/migration-input-v4.json")
    violations = 0
    for name in releases:
        doc = load("contracts/openapi/" + name)
        if name == "inventory-native-input-v1.3.json":
            if doc["components"]["schemas"]["MigrationInput"] != canonical:
                raise ValueError("Canonical Inventory migration component schema drift")
            # Canonical v4 is independently pinned to the installed Planning
            # consumer; don't impose newer URL-UUID rules on its embedded fields.
            del doc["components"]["schemas"]["MigrationInput"]
        def visit(node, pointer=""):
            nonlocal violations
            if isinstance(node, list):
                for index, item in enumerate(node):
                    visit(item, f"{pointer}/{index}")
            elif isinstance(node, dict):
                if node.get("format") == "uuid":
                    pattern = node.get("pattern")
                    if pattern != UUID_PATTERN and not (
                        name == "inventory-native-input-v1.3.json"
                        and pattern == UUID_V4_PATTERN
                        and "/get/parameters/" in pointer
                    ):
                        violations += 1
                        raise ValueError(f"Noncanonical UUID in current authority release {name}: {pointer}")
                for key, value in node.items():
                    visit(value, f"{pointer}/{key}")
        visit(doc)
    return violations



def check_error_policy():
    """New authority releases must use the exact common error envelope.

    Existing published APIs are historical and are not mutated retroactively.
    The schema allows the already-emitted {"error": "..."} and Laravel
    {"message": "...", "errors": {...}} forms until a future reviewed version.
    """
    expected = load("contracts/schemas/common/error-v1.json")
    for key in ("$schema", "$id", "title"):
        expected.pop(key, None)
    releases = (
        "catalogue-internal-v1.json",
        "inventory-native-input-v1.3.json",
        "inventory-collection-worker-v1.json",
        "planning-qualification-events-v1.json",
        "lifecycle-internal-authority-v1.json",
        "governance-service-checks-v1.json",
        "assurance-qualification-v1.json",
        "governance-inventory-collection-v1.1.json",
        "governance-native-approval-v1.1.json",
    )
    for name in releases:
        document = current = load("contracts/openapi/" + name)
        if current["components"]["schemas"].get("Error") != expected:
            raise ValueError(f"Shared owner error schema drift: {name}")
        for endpoint, path_item in document["paths"].items():
            for method, operation in path_item.items():
                if method not in {"get", "post", "put", "patch", "delete"}:
                    continue
                for status, response in operation["responses"].items():
                    if status.startswith("2"):
                        continue
                    schema = (response.get("content", {})
                              .get("application/json", {}).get("schema"))
                    if schema != {"$ref": "#/components/schemas/Error"}:
                        raise ValueError(
                            f"Owner error body not contracted: {name}:{method} {endpoint}:{status}"
                        )


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
    check_owner_operation_bindings()
    check_implemented_api_contracts()
    check_uuid_policy()
    check_error_policy()
    print(json.dumps(dict(status="PASS", sources=sources, bundles=bundles, unique_ids=id_count, schema_count=schema_count, paths=paths, operations=ops)))

if __name__ == "__main__":
    main()
