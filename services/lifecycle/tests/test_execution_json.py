"""Reject ambiguous or nonfinite owner and API JSON before canonical binding."""

import pytest

from lifecycle.domain.execution import decode


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity", "1e999", "-1e999"])
def test_nonfinite_json_cannot_be_reinterpreted_as_optional_null(number: str) -> None:
    with pytest.raises(ValueError, match="nonfinite_json_number"):
        decode(('{"members":[{"outage_group":' + number + "}]}").encode())


def test_finite_numbers_and_explicit_null_retain_their_meaning() -> None:
    assert decode(b'{"optional":null,"ratio":1.25,"counter":9007199254740993}') == {
        "optional": None,
        "ratio": 1.25,
        "counter": 9007199254740993,
    }


def test_nested_duplicate_keys_remain_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate_key"):
        decode(b'{"scope":{"tenant_id":"first","tenant_id":"second"}}')
