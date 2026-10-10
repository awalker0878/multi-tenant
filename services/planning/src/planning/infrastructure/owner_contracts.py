"""Executable, typed owner-operation to immutable installed response schema mapping.

Only one contract is admissible for a particular owner, method and path.
Unknown operations, method drift and obsolete declared schema versions fail closed.
Do not substitute generic response-name allowlists: the endpoint selects the type.
"""
from __future__ import annotations

import re

# (owner, HTTP verb, anchored path pattern, installed schema basename)
OWNER_OPERATIONS: tuple[tuple[str, str, str, str], ...] = (
    ("CATALOGUE", "GET",
     r"/v1/tenants/[^/]+/planning-inputs/[^/]+/[^/]+/[^/]+/[^/]+",
     "catalogue-input-v1"),
    ("CATALOGUE", "GET",
     r"/internal/tenants/[^/]+/applications/[^/]+/environments/[^/]+/current-planning-intent",
     "catalogue-current-v2"),
    ("INVENTORY", "GET",
     r"/(?:internal|v1)/tenants/[^/]+/planning-capability-inputs/[^/]+/[^/]+/[^/]+/[^/]+/[^/]+",
     "inventory-input-v2"),
    ("INVENTORY", "GET",
     r"/(?:internal|v1)/tenants/[^/]+/migration-inputs/[^/]+/[^/]+/[^/]+/[1-9][0-9]{0,8}/[0-9a-f]{64}",
     "migration-input-v4"),
    ("ASSURANCE", "POST", r"/v1/tenants/[^/]+/planning-qualification-v2",
     "qualification-v2.1"),
    ("ASSURANCE", "POST", r"/internal/tenants/[^/]+/qualification-checks",
     "qualification-v2.1"),
    ("ASSURANCE", "POST", r"/v1/tenants/[^/]+/migration-qualifications",
     "migration-support-v2"),
)


def contract_for_operation(
    owner: str, method: str, path: str, requested: str | None = None
) -> str:
    matches = [
        schema for candidate, verb, pattern, schema in OWNER_OPERATIONS
        if candidate == owner and method == verb and re.fullmatch(pattern, path)
    ]
    if len(matches) != 1 or (requested is not None and requested != matches[0]):
        raise ValueError("owner_contract_operation_unavailable")
    return matches[0]
