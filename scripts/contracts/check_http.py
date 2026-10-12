"""Native authority, exact owner APIs, UUID and error contract invariants."""
from __future__ import annotations
import json
import re
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from check_schema import load
ROOT = Path(__file__).resolve().parents[2]

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
        ("PlanningInput", "contracts/schemas/planning/inventory-input-v1.json", None),
        ("CapabilityInput", "contracts/schemas/planning/inventory-input-v2.json",
         "services/planning/src/planning/infrastructure/inputs/inventory-input-v2.json"),
    ):
        reference = normalize_uuids(load(source))
        if inv_api["components"]["schemas"][embedded] != reference or (installed is not None and load(source) != load(installed)):
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


def check_owner_response_projections():
    """Current bounded response profiles must reflect their owner-authored API and producer."""
    delegation = load("contracts/openapi/governance-delegation-v1.1.json")
    projected = load("contracts/schemas/planning/governance-delegation-response-v1.json")
    embedded = json.loads(json.dumps(delegation["components"]["schemas"]["CurrentDelegation"]))
    embedded["properties"]["scope"] = {"$ref": "#/$defs/Scope"}
    projected_scope = projected.pop("$defs", None)
    for key in ("$id", "$schema", "title"):
        projected.pop(key, None)
    if projected != embedded or projected_scope != {"Scope": delegation["components"]["schemas"]["Scope"]}:
        raise ValueError("Planning Governance response differs from published owner API")
    receipt = load("contracts/schemas/planning/placement-reservation-v1.json")
    required = {"tenant_id", "plan_digest", "placement_sha256", "allocations",
                "state", "observed_at", "expires_at", "native_write_authorized"}
    if (not required <= set(receipt.get("required", []))
            or receipt.get("additionalProperties") is not False
            or receipt.get("properties", {}).get("native_write_authorized") != {"const": False}):
        raise ValueError("Lifecycle placement receipt lacks bounded authority invariants")


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
