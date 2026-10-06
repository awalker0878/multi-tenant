"""Bounded Inventory outbox delivery command; no actor or native credentials are used."""

import argparse
from collections.abc import Sequence

from inventory.application.events import publish_one
from inventory.infrastructure.publisher import publish
from inventory.infrastructure.store import Postgres


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inventory-publish", allow_abbrev=False)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 100:
        parser.error("limit must be between 1 and 100")
    try:
        for _ in range(args.limit):
            if not publish_one(Postgres(), publish):
                break
        return 0
    except Exception:
        print('{"status":"delivery_unavailable"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
