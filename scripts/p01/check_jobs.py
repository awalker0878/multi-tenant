#!/usr/bin/env python3
"""Fail the stable required check unless every selected build family succeeded."""
import argparse
import json
import os
from pathlib import Path


def check(needs: dict, families: list[str], components: dict) -> None:
    selection = needs.get("selection", {})
    if selection.get("result") != "success":
        raise ValueError("Component selection did not succeed")
    for family in families:
        raw = selection.get("outputs", {}).get(family)
        if not isinstance(raw, str):
            raise ValueError(f"Missing {family} selection output")
        selected = json.loads(raw)
        if not isinstance(selected, list) or any(not isinstance(value, str) for value in selected):
            raise ValueError(f"Invalid {family} selection output")
        if len(selected) != len(set(selected)) or any(value not in components for value in selected):
            raise ValueError(f"Unknown or repeated {family} component")
        if family in {"python", "php"} and any(components[value]["language"] != family for value in selected):
            raise ValueError(f"Incorrect language in {family} selection")
        expected = "success" if selected else "skipped"
        actual = needs.get(family, {}).get("result")
        if actual != expected:
            raise ValueError(f"{family} result {actual!r}; expected {expected!r} for {len(selected)} selected components")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--family", action="append", required=True)
    args = parser.parse_args()
    components = json.loads((args.workspace / "scripts/p01/candidates.json").read_text())["components"]
    check(json.loads(os.environ["P01_NEEDS_JSON"]), args.family, components)
    print("Every selected foundation family succeeded; skipped families have an empty selection.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
