"""Registered typed comparisons; unknown requirements cannot become positive claims."""

from fnmatch import fnmatchcase
from typing import Any

from planning.domain.capability_definitions import MATCHERS
from planning.domain.model import digest


def matches(key: str, requested: Any, values: list[Any]) -> bool | None:
    definition = MATCHERS.get(key)
    if definition is None:
        choices = [v for pattern, v in MATCHERS.items() if fnmatchcase(key, pattern)]
        if len(choices) != 1:
            return None
        definition = choices[0]
    comparison, unit = definition
    if comparison == "exact":
        return digest(requested) in [digest(v) for v in values]
    if comparison != "maximum" or not values:
        return False

    def quantity(value: Any) -> int | None:
        if isinstance(value, dict):
            if set(value) != {"value", "unit"} or value["unit"] != unit:
                return None
            value = value["value"]
        # v1 numeric fields have the unit in their canonical field identifier.
        if type(value) is not int or not 0 <= value <= 9007199254740991:
            return None
        return value

    target = quantity(requested)
    measured = [quantity(v) for v in values]
    # An unscoped v1 list cannot select only its fastest restore. Every bound must fit.
    return target is not None and all(v is not None and v <= target for v in measured)
