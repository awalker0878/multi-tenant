"""Cross-language SHA-256 goldens pinned by the Assurance/Planning scope contract."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from planning.domain.model import digest

VECTORS = (
    Path(__file__).resolve().parents[3]
    / "contracts/fixtures/qualification-scope-digests-v1.json"
)


def test_php_python_scope_sha256_golden_vectors_match() -> None:
    vectors = json.loads(VECTORS.read_text(encoding="utf-8"))
    assert vectors["schema_version"] == 1
    assert len(vectors["cases"]) == 2
    for vector in vectors["cases"]:
        scope: dict[str, Any] = vector["scope"]
        assert digest(scope) == vector["sha256"]
        # DB-native JSONB key reordering must not change scope identity.
        assert digest(dict(reversed(list(scope.items())))) == vector["sha256"]


@pytest.mark.parametrize("field", ["tenant_id", "site_id", "endpoint_id", "native_scope", "method"])
def test_scope_identity_changes_when_any_authentication_dimension_changes(field: str) -> None:
    scope: dict[str, Any] = json.loads(VECTORS.read_text(encoding="utf-8"))["cases"][0]["scope"]
    original = digest(scope)
    other = deepcopy(scope)
    other[field] = str(other[field]) + "-changed"
    assert digest(other) != original
