"""Validate untrusted wire data before generated decoding and scoped translation."""

import json
from datetime import datetime
from importlib.resources import files

from jsonschema import Draft202012Validator, FormatChecker

from planning.domain.model import Rejected
from planning.domain.model import decode as decode_object
from planning.infrastructure.messaging.generated import GeneratedEvent

SCHEMA = json.loads(files(__package__).joinpath("foundation-event.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def decode(wire: bytes) -> GeneratedEvent:
    if len(wire) > 4096:
        raise ValueError("invalid_event")
    try:
        value = decode_object(wire)
    except Rejected:
        raise ValueError("invalid_event") from None
    VALIDATOR.validate(value)
    datetime.strptime(value["occurred_at"], "%Y-%m-%dT%H:%M:%SZ")
    value["schema_version"] = int(value["schema_version"])
    return GeneratedEvent(**value)


def canonical(event: GeneratedEvent) -> bytes:
    return json.dumps(vars(event), sort_keys=True, separators=(",", ":")).encode("ascii")
