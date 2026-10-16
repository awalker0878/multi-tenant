"""Installed wire-schema validator at Planning's infrastructure boundary.

The application receives this callable through its constructor. No infrastructure
or JSON Schema dependency crosses into the application or domain layer.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from planning.domain.model import Rejected


@lru_cache(maxsize=1)
def _workload_validator() -> Draft202012Validator:
    schema = json.loads(
        files("planning.infrastructure.inputs")
        .joinpath("migration-readiness-v2.2.json")
        .read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_workload_contract(result: dict[str, Any]) -> None:
    """Fail closed on invalid or partially produced migration readiness.

    This is a transport contract check, not independent E3/E4 qualification.
    """
    if not _workload_validator().is_valid(result):
        raise Rejected("migration_workload_contract_invalid", 423)
