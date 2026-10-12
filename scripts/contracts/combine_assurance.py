"""Combine ephemeral, measured service-owned assurance observations into a coverage report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from assurance import assess


def combine(folder: Path) -> list[dict]:
    # No checked-in JSON ledger can qualify a service. Only files created in
    # ephemeral CI job workspaces are accepted by the workflow's download step.
    paths = sorted(folder.rglob("*.json"))
    if not paths:
        raise ValueError("No executed contract assurance evidence was provided")
    evidence = []
    for file in paths:
        value = json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(value, list):
            raise ValueError(f"Malformed measured contract assurance evidence: {file}")
        evidence.extend(value)
    if not evidence:
        raise ValueError("Empty measured contract assurance evidence")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--require-qualified", action="store_true")
    args = parser.parse_args()
    outcome = assess(observations=combine(args.input_directory),
                     require_provenance=args.require_qualified)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    missing = (outcome["summary"]["unqualified_http_operations"]
               + outcome["summary"]["unqualified_canonical_releases"])
    by_claim = {}
    for row in [*outcome["coverage"], *(
            release for release in outcome["release_coverage"]
            if release["kind"] != "openapi")]:
        for claim in row["missing"]:
            by_claim[claim] = by_claim.get(claim, 0) + 1
    print(json.dumps({"summary": outcome["summary"], "missing_by_claim": by_claim},
                     indent=2, sort_keys=True))
    # An incomplete report is a diagnostic, never a passing assurance decision.
    # A release/qualification gate must explicitly request all evidence.
    return int(args.require_qualified and missing > 0)


if __name__ == "__main__":
    raise SystemExit(main())
