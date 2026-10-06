"""Compare protected P07 records and saved-plan bytes locally; never run Terraform."""

import argparse
import hashlib
import json
import time
from collections.abc import Sequence
from pathlib import Path

from lifecycle.domain.execution import Rejected
from lifecycle.domain.native_preflight import assess_saved_plan
from lifecycle.interfaces.commissioning import read_json, read_regular


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("plan", "commissioning", "toolchain", "snapshot", "saved-plan"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = assess_saved_plan(
            read_json(args.plan),
            read_json(args.commissioning),
            read_json(args.toolchain),
            read_json(args.snapshot),
            hashlib.sha256(read_regular(args.saved_plan, 64 * 1024 * 1024)).hexdigest(),
            int(time.time()),
        )
    except Rejected as error:
        print(
            json.dumps(
                {
                    "result": "INVALID",
                    "error": error.reason,
                    "native_write_authorized": False,
                    "retry_authorized": False,
                }
            )
        )
        return 1
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        print(
            json.dumps(
                {
                    "result": "INVALID",
                    "error": "invalid_input",
                    "native_write_authorized": False,
                    "retry_authorized": False,
                }
            )
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result["holds"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
