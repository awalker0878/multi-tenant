"""AsyncAPI channel ownership, message discriminators and schema references."""
from __future__ import annotations
from pathlib import Path
from contract_io import read
from jsonschema import Draft202012Validator, FormatChecker
from check_schema import local_refs
ROOT = Path(__file__).resolve().parents[2]

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
        document = read(path)
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
            schema = read(event)
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
