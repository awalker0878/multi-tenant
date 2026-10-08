"""Versioned movement budgets. Time never substitutes for current write authority."""

from typing import Any

from lifecycle_worker.application.native import NativeHeld


def seconds(plan: dict[str, Any]) -> int:
    version, value = plan.get("schema_version"), plan.get("max_seconds")
    if type(version) is not int or version not in {1, 2, 3}:
        raise NativeHeld("migration_budget_version_invalid")
    maximum = 600 if version == 1 else 86400
    if type(value) is not int or not 1 <= value <= maximum:
        raise NativeHeld("migration_time_budget_invalid")
    return value
