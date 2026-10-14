"""Active canonical releases, live owner bindings, and installed consumers."""
from __future__ import annotations
import json
import re
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from check_schema import load
from runtime_inventory import verify_runtime_inventory
from installed_usage import verify_installed_usage
ROOT = Path(__file__).resolve().parents[2]

def check_consumer_registry():
    registry = load("architecture/contract-consumers.json")
    inventory = registry["contracts"]
    releases = registry.get("active_releases")
    if not isinstance(releases, list) or not releases:
        raise ValueError("Missing machine-readable active contract release catalogue")
    names = [entry["path"] for entry in releases]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate active canonical contract release")
    if set(names) != set(inventory):
        raise ValueError("Active contract registry does not cover every declared consumer")
    active = set(names)
    # Only current canonical releases are shipped. Every installed consumer
    # and generated loader must target the active release set directly.
    # Each live service operation belongs to exactly one active versioned owner
    # release; obsolete canonical bundles are removed from the working tree.
    seen_operations = {}
    # Native authority/effect endpoints are single deployed boundaries even
    # if duplicate specs incorrectly declare different owner strings.
    native_operations = {}
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
                if endpoint.startswith("/internal/native-"):
                    native_key = (method.upper(), endpoint)
                    if native_key in native_operations:
                        raise ValueError(
                            f"Overlapping native wire operation: {native_key} in "
                            f"{native_operations[native_key]} and {entry['path']}"
                        )
                    native_operations[native_key] = entry["path"]
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
        # Owners/consumers are registered deployable bounded contexts, not
        # keys of a separately editable architectural dependency DAG.
        from artifact_attestation import COMPONENTS
        known_contexts = {context for context, _ in COMPONENTS.values()} | {"contract-platform"}
        if (not (ROOT / path).is_file()
                or owner not in known_contexts
                or set(consumers) - known_contexts):
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
    # A canonical bundle cannot be left in the checkout as undocumented history.
    canonical = set()
    for area in ("asyncapi", "capabilities", "openapi", "platforms", "schemas"):
        for suffix in ("*.json", "*.yaml", "*.yml"):
            canonical.update(
                str(path.relative_to(ROOT))
                for path in (ROOT / "contracts" / area).rglob(suffix)
            )
    if canonical != set(names):
        raise ValueError("Canonical contracts outside active releases: " + repr(sorted(canonical - set(names)))
                         + "; active releases without canonical files: " + repr(sorted(set(names) - canonical)))
    verify_runtime_inventory(registry, ROOT)
    verify_installed_usage(ROOT, registry)


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
        ("GOVERNANCE", "governance-delegation-response-v2"),
        ("LIFECYCLE", "placement-reservation-v1"),
    }
    present = set()
    for owner, method, pattern, schema in operations:
        if owner not in {"CATALOGUE", "INVENTORY", "ASSURANCE", "GOVERNANCE", "LIFECYCLE"} or method not in {"GET", "POST"}:
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
