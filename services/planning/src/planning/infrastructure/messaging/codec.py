"""Validate untrusted wire data before generated decoding and scoped translation."""

import json
from datetime import datetime
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from planning.infrastructure.messaging.generated import GeneratedEvent

SCHEMA = json.loads(files(__package__).joinpath("foundation-event.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def decode(wire: bytes) -> GeneratedEvent:
    if len(wire) > 4096:
        raise ValueError("invalid_event")
    value: Any = json.loads(wire)
    VALIDATOR.validate(value)
    datetime.strptime(value["occurred_at"], "%Y-%m-%dT%H:%M:%SZ")
    value["schema_version"] = int(value["schema_version"])
    return GeneratedEvent(**value)


def canonical(event: GeneratedEvent) -> bytes:
    return json.dumps(vars(event), sort_keys=True, separators=(",", ":")).encode("ascii")
