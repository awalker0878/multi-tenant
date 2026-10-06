"""Pure execution invariants. E2 simulation never grants native authority."""

import json
import re
from typing import Any
from uuid import UUID

from lifecycle.domain.admission import digest


class Rejected(Exception):
    def __init__(self, reason: str, status: int = 409) -> None:
        self.reason, self.status = reason, status
        super().__init__(reason)


def identity(value: Any) -> str:
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise Rejected("invalid_identity", 422)
    return value


def shape(value: Any, keys: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise Rejected("invalid_shape", 422)


def decode(raw: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate_key")
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: None)
    if not isinstance(value, dict):
        raise Rejected("invalid_shape", 422)
    return value


def execution_plan(content: dict[str, Any], binding: dict[str, Any]) -> list[str]:
    if content.get("lane") != "isolated_campaign" or binding.get("lane") != "isolated_campaign":
        raise Rejected("p06_simulation_only", 403)
    if content.get("action") not in {
        "application.provision",
        "application.migrate",
        "application.recover",
        "application.retire",
    }:
        raise Rejected("unsupported_action", 422)
    effects = content.get("effects")
    if not isinstance(effects, list) or not 1 <= len(effects) <= 32:
        raise Rejected("effect_bound", 422)
    seen: list[str] = []
    for effect in effects:
        name = effect.get("id", "")
        if (
            not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name)
            or name in seen
            or not isinstance(effect.get("after"), list)
            or not set(effect["after"]).issubset(seen)
            or effect.get("scope") != content.get("scope")
            or effect.get("on_unknown") != "hold_and_observe_before_retry"
            or effect.get("authority_recheck") != "immediately_before_effect"
        ):
            raise Rejected("invalid_effect_contract", 422)
        seen.append(name)
    if not content.get("ownership"):
        raise Rejected("ownership_required", 422)
    return seen


def hold_keys(content: dict[str, Any]) -> list[str]:
    scope = content["scope"]
    # Environment/application IDs cannot partition ownership of the same native field.
    base = {k: scope[k] for k in ("tenant_id", "site_id", "endpoint_id", "native_scope")}
    keys = {digest({**base, "resource": scope["resource_id"], "field": "application_writer"})}
    for owner in content["ownership"]:
        if not owner.get("fields") or not owner.get("writer") or not owner.get("resource"):
            raise Rejected("ownership_required", 422)
        for field in owner["fields"]:
            keys.add(digest({**base, "resource": owner["resource"], "field": field}))
    return sorted(keys)


def recovery_mode(content: dict[str, Any], operations: list[dict[str, Any]]) -> str:
    writes = {e["id"] for e in content["effects"] if e["boundary"] == "target_first_write"}
    if any(o["step"] in writes and o["outcome"] != "not_started" for o in operations):
        return "forward_recovery_required"
    return "pre_target_write_reconciliation"
