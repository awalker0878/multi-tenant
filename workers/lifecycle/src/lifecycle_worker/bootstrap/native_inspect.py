"""Read-only native API plan inspection and independently scoped object observation."""

import argparse
import json
import time
from pathlib import Path

from lifecycle_worker.application.api_plan import validate_api_plan
from lifecycle_worker.application.native import NativeBinding, NativeHeld, decode
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.native_http import NativeReads
from lifecycle_worker.infrastructure.native_runtime import endpoints, runtime
from lifecycle_worker.infrastructure.openstack_readback import OpenStackReadback


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--observe", action="store_true")
    parser.add_argument("--receipts", type=Path)
    args = parser.parse_args()
    try:
        binding = NativeBinding.parse(decode(protected_read(args.binding, 65536)))
        config = runtime(args.runtime)
        resources = validate_api_plan(
            decode(protected_read(Path(config["operation_plan"]), 1_048_576)), binding
        )
        if args.observe:
            if args.receipts is None:
                raise NativeHeld("native_receipts_required")
            observer, writer = config["observer"], config["writer"]
            adapter = OpenStackReadback(
                NativeReads(endpoints(observer["endpoints"])),
                resources,
                observer["user_id"],
                writer["user_id"],
                lambda: int(time.time()),
            )
            result = adapter.observe(binding, decode(protected_read(args.receipts, 65536)))
        else:
            result = {
                "operation_plan_sha256": binding.operation_plan_sha256,
                "resource_count": len(resources),
            }
        print(
            json.dumps(
                {"result": result, "native_write_authorized": False, "retry_authorized": False}
            )
        )
        return 2 if result.get("outcome") == "held" else 0
    except (NativeHeld, OSError, ValueError, KeyError, TypeError):
        print(
            json.dumps(
                {
                    "result": "HELD",
                    "reason": "native_inspection_unavailable",
                    "native_write_authorized": False,
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
