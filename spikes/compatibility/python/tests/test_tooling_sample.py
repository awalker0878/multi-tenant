"""Behavioral checks for the disposable layering fixture."""

import pytest
from pydantic import ValidationError

from probe_inventory.application.advance import advance
from probe_inventory.bootstrap import probe
from probe_inventory.domain.sample import Sample
from probe_inventory.infrastructure.memory import MemoryStore
from probe_inventory.infrastructure.transport import host
from probe_inventory.interfaces.payload import parse_label
from probe_planning.bootstrap import probe as planning_probe


def test_owned_entrypoint_and_adapter() -> None:
    assert probe() == 1
    assert planning_probe() == "sample-1"
    assert host() == "compatibility.invalid"


def test_transition_preserves_input_and_persists_result() -> None:
    store = MemoryStore()
    original = Sample("synthetic")
    updated = advance(original, store)
    assert original.revision == 0
    assert updated.revision == 1
    assert store.saved == [updated]


def test_invalid_transition_does_not_write() -> None:
    store = MemoryStore()
    with pytest.raises(ValueError, match="negative"):
        advance(Sample("synthetic", revision=-1), store)
    assert store.saved == []


def test_boundary_validation() -> None:
    assert parse_label('{"label":"synthetic"}') == "synthetic"
    with pytest.raises(ValidationError):
        parse_label('{"label":123}')
    with pytest.raises(ValidationError):
        parse_label('{"label":"synthetic","unexpected":true}')
