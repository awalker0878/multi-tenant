"""Active contract integrity: explicit invariant owners, no historical adapters."""
from __future__ import annotations
import json

from build import verify
from check_schema import (
    unique_schema_ids, current_api,
    check_schema_dialects, check_readiness_projection, load,
)
from check_events import check_events
from check_registry import check_consumer_registry, check_owner_operation_bindings
from check_http import (
    check_native_candidates, check_implemented_api_contracts,
    check_uuid_policy, check_error_policy, check_owner_response_projections,
)


def main():
    sources, bundles = verify()
    id_count = unique_schema_ids()
    schema_count = check_schema_dialects()
    paths, ops = 0, 0
    active = load("architecture/contract-consumers.json")["active_releases"]
    apis = sorted(entry["path"].rsplit("/", 1)[-1] for entry in active
                  if entry["path"].startswith("contracts/openapi/"))
    for name in apis:
        a, b = current_api(name)
        paths += a
        ops += b
    check_native_candidates()
    check_events()
    check_readiness_projection()
    check_consumer_registry()
    check_owner_operation_bindings()
    check_implemented_api_contracts()
    check_owner_response_projections()
    check_uuid_policy()
    check_error_policy()
    print(json.dumps(dict(status="PASS", sources=sources, bundles=bundles, unique_ids=id_count, schema_count=schema_count, paths=paths, operations=ops)))

if __name__ == "__main__":
    main()
