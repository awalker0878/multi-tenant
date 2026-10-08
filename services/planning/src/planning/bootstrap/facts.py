"""Bounded separate facts process; no native credentials or dispatch."""

import argparse
import time
from collections.abc import Sequence

from planning.application.events import publish_one
from planning.application.planning import Planning
from planning.application.validation import PlanValidation
from planning.infrastructure.facts.broker import connection, consume_one, publish
from planning.infrastructure.owners import OwnerSources
from planning.infrastructure.store import Postgres


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="planning-facts", allow_abbrev=False)
    parser.add_argument("operation", choices=["publish", "inventory", "catalogue"])
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 100:
        parser.error("limit must be between 1 and 100")
    try:
        database = Postgres()
        if args.operation == "publish":
            for _ in range(args.limit):
                if not publish_one(database, publish):
                    break
        else:
            conn = connection()
            try:
                channel = conn.channel()
                channel.basic_qos(prefetch_count=1)

                def clock() -> int:
                    return int(time.time())

                service = Planning(
                    database, OwnerSources(), clock, PlanValidation.unavailable(clock)
                )
                for _ in range(args.limit):
                    if consume_one(channel, service, args.operation) == "empty":
                        break
            finally:
                conn.close()
        return 0
    except Exception:
        print('{"status":"planning_delivery_unavailable"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
