"""Sign an existing owner observation against a downloaded commissioning packet."""

import argparse
from collections.abc import Sequence

from inventory.infrastructure.readiness_publication import publish


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("packet", "report", "producer", "key", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        publish(args.packet, args.report, args.producer, args.key, args.output)
    except Exception:
        print('{"status":"publication_held","native_write_authorized":false}')
        return 1
    print('{"status":"owner_receipt_written","native_write_authorized":false}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
