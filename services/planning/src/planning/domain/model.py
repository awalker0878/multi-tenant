"""Canonical semantic JSON and bounded identities; no source may confer authority."""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from planning.domain.capability_definitions import ACTIONS as ACTIONS
from planning.domain.capability_definitions import DIMENSIONS as DIMENSIONS
from planning.domain.capability_definitions import PLATFORMS as PLATFORMS

CANONICALIZATION = "p05-json-v1"


class Rejected(Exception):
    def __init__(self, reason: str, status: int = 422) -> None:
        self.reason, self.status = reason, status
        super().__init__(reason)


def identifier(value: Any) -> str:
    if not isinstance(value, str):
        raise Rejected("invalid_identity")
    try:
        parsed = UUID(value)
        if str(parsed) != value or parsed.variant != "specified in RFC 4122":
            raise ValueError
    except ValueError:
        raise Rejected("invalid_identity") from None
    return value


def shape(value: Any, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.keys() != keys:
        raise Rejected("invalid_shape")
    return value


def sha(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{64}", value):
        raise Rejected("invalid_digest")
    return value


def integer(value: Any, minimum: int = 0, maximum: int = 2**53 - 1) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise Rejected("invalid_integer")
    return value


def canonical(value: Any) -> str:
    def check(v: Any, depth: int = 0) -> None:
        if depth > 32:
            raise Rejected("input_depth")
        if v is None or isinstance(v, bool):
            return
        if type(v) is int:
            integer(v, -(2**53 - 1))
        elif isinstance(v, str):
            if len(v) > 4096 or any(0xD800 <= ord(c) <= 0xDFFF for c in v):
                raise Rejected("invalid_string")
        elif isinstance(v, list):
            if len(v) > 1000:
                raise Rejected("input_bound")
            for item in v:
                check(item, depth + 1)
        elif isinstance(v, dict):
            for key, item in v.items():
                if not isinstance(key, str) or not key.isascii():
                    raise Rejected("invalid_key")
                if key.lower() in {"password", "secret", "token", "private_key", "credential"}:
                    raise Rejected("secret_material_forbidden")
                check(item, depth + 1)
        else:
            raise Rejected("noncanonical_value")

    check(value)
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class Actor:
    tenant: str
    actor: str
    action: str
    application: str
    environment: str


def profile(platform: str, version: str, declarations: dict[str, Any]) -> dict[str, Any]:
    if platform not in PLATFORMS or not re.fullmatch(r"[a-zA-Z0-9._-]{1,64}", version):
        raise Rejected("invalid_profile")
    if declarations.keys() - set(DIMENSIONS):
        raise Rejected("unknown_dimension")
    rows = []
    for dimension in DIMENSIONS:
        declaration = declarations.get(dimension, {"status": "unknown", "operations": []})
        shape(declaration, {"status", "operations"})
        if declaration["status"] not in {"unknown", "unsupported", "declared"}:
            raise Rejected("invalid_declaration")
        if not isinstance(declaration["operations"], list) or any(
            operation not in ACTIONS for operation in declaration["operations"]
        ):
            raise Rejected("invalid_operation")
        rows.append({"dimension": dimension, "declaration": declaration})
    result = {"platform": platform, "version": version, "dimensions": rows}
    return result | {"digest": digest(result)}


def decode(raw: bytes) -> dict[str, Any]:
    def pairs(rows: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for k, v in rows:
            if k in output:
                raise Rejected("duplicate_json_key")
            output[k] = v
        return output

    try:
        value = json.loads(
            raw,
            object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise Rejected("invalid_json") from None
