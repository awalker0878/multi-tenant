"""Current Planning readiness schema admission at Lifecycle's transport boundary.

The domain verifier only compares typed values, digests and independently
retrieved scope/evidence. The installed canonical schema is owned here.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from lifecycle.domain.execution import Rejected
from lifecycle.domain.migration_readiness import REQUIRED
from lifecycle.domain.migration_readiness import verify as verify_domain


@lru_cache(maxsize=1)
def _readiness_validator() -> Draft202012Validator:
    schema = json.loads(
        files("lifecycle.infrastructure.contracts")
        .joinpath("migration-readiness-v2.2.json")
        .read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def verify(value: Any, content: dict[str, Any], tenant: str, now: int) -> None:
    if not isinstance(value, dict) or set(value) != REQUIRED:
        raise Rejected("migration_readiness_missing", 423)
    if not _readiness_validator().is_valid(value):
        raise Rejected("migration_readiness_contract_invalid", 423)
    verify_domain(value, content, tenant, now)
