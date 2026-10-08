"""Probe commissioned migration accounts without creating, changing or deleting a VM."""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from lifecycle_worker.infrastructure.migration_accounts import MigrationAccountProbe


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lifecycle-migration-accounts", allow_abbrev=False)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(MigrationAccountProbe(args.config).run(), sort_keys=True))
        return 0
    except Exception:
        print(
            '{"accounts_checked":false,"status":"migration_accounts_held","native_write_authorized":false}'
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
