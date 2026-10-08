"""Compose the small installed Inventory worker diagnostic command."""

import argparse
import json
from collections.abc import Sequence

from inventory_worker.interfaces.health import Probe, probe


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="inventory-worker-health",
        description=(
            "Inventory worker bootstrap diagnostic. Liveness checks this process only; "
            "worker dependency readiness is not implemented."
        ),
        allow_abbrev=False,
    )
    parser.add_argument("probe", choices=[mode.value for mode in Probe])
    args = parser.parse_args(argv)
    status, result = probe(Probe(args.probe))
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
