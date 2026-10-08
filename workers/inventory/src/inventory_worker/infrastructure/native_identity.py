"""Canonical native UUIDs without inferring a platform or authority."""

import re
from typing import Any

from inventory_worker.infrastructure.native import CollectionFailure


def native_id(value: Any) -> str:
    if (
        not isinstance(value, str)
        or re.fullmatch(r"[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}", value) is None
    ):
        raise CollectionFailure("invalid_response")
    return value
