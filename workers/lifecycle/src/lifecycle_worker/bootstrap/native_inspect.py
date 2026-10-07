"""Read-only native bundle inspection. There is deliberately no CLI apply switch."""

import argparse
import json
import time
from pathlib import Path

from lifecycle_worker.application.native import NativeBinding, NativeHeld, decode
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.native_http import NativeEndpoint, NativeReads
from lifecycle_worker.infrastructure.openstack_readback import OpenStackReadback
from lifecycle_worker.infrastructure.terraform import TerraformSavedPlan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--observe", action="store_true")
    args = parser.parse_args()
    try:
        binding = NativeBinding.parse(decode(protected_read(args.binding, 65536)))
        config = decode(protected_read(args.runtime, 65536))
        if set(config) != {
            "terraform_executable",
            "bundle_root",
            "environment",
            "credential_files",
            "observer",
        }:
            raise NativeHeld("invalid_native_runtime")
        tool = TerraformSavedPlan(
            Path(config["terraform_executable"]),
            Path(config["bundle_root"]),
            config["environment"],
            {k: Path(v) for k, v in config["credential_files"].items()},
        )
        if args.observe:
            observer = config["observer"]
            if set(observer) != {"endpoints", "user_id", "writer_user_id"}:
                raise NativeHeld("invalid_native_observer")
            reads = NativeReads(
                {
                    name: NativeEndpoint(
                        row["base_url"],
                        row["address"],
                        Path(row["ca_file"]),
                        Path(row["token_file"]),
                    )
                    for name, row in observer["endpoints"].items()
                }
            )
            adapter = OpenStackReadback(
                reads,
                tool.verified(binding)["resources"],
                observer["user_id"],
                observer["writer_user_id"],
                lambda: int(time.time()),
            )
            result = adapter.observe(binding, tool.state(binding))
        else:
            result = tool.inspect(binding)
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
