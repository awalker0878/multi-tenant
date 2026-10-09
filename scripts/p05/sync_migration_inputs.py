#!/usr/bin/env python3
"""Single-source strict Inventory→Planning workload owner contract.

Run after changing contracts/schemas/planning/migration-input-v3.json.
--check verifies the package installed inside Planning's isolated container.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "contracts/schemas/planning/migration-input-v3.json"
TARGET = ROOT / "services/planning/src/planning/infrastructure/inputs/migration-input-v3.json"


def main() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument("--check", action="store_true")
    args = cli.parse_args()
    source = json.loads(SOURCE.read_text())
    expected = json.dumps(source, indent=2, ensure_ascii=True) + "\n"
    if args.check:
        if not TARGET.is_file() or json.loads(TARGET.read_text()) != source:
            print("Planning's installed migration-input-v3 schema drifted from canonical contract")
            return 1
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(expected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
