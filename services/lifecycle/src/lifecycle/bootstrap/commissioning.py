"""Offline P07 commissioning review: no credentials, networking or native effects."""

import argparse
import json
import time
from collections.abc import Sequence
from pathlib import Path

from lifecycle.domain.commissioning import assess
from lifecycle.domain.execution import Rejected
from lifecycle.interfaces.commissioning import read_json


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = assess(read_json(args.input), int(time.time()))
    except Rejected as error:
        print(
            json.dumps(
                {"record_valid": False, "error": error.reason, "native_write_authorized": False}
            )
        )
        return 1
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        print(
            json.dumps(
                {"record_valid": False, "error": "invalid_input", "native_write_authorized": False}
            )
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if args.require_complete and not result["record_complete"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
