"""Long transfers remain explicit, bounded and incompatible with implicit v1 widening."""

from typing import Any

import pytest

from lifecycle_worker.application.native import NativeHeld
from lifecycle_worker.infrastructure.migration_budget import seconds


@pytest.mark.parametrize(
    "version,budget", [(1, 1), (1, 600), (2, 601), (2, 3600), (2, 86400), (3, 86400)]
)
def test_explicit_stage_budgets(version: int, budget: int) -> None:
    assert seconds({"schema_version": version, "max_seconds": budget}) == budget


@pytest.mark.parametrize(
    "version,budget", [(1, 601), (2, 86401), (True, 600), (2, True), (4, 600), (2, 0), (2, "3600")]
)
def test_budget_cannot_be_widened_or_implicitly_coerced(version: Any, budget: Any) -> None:
    with pytest.raises(NativeHeld):
        seconds({"schema_version": version, "max_seconds": budget})
