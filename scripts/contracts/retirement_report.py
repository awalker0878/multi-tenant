"""Report actual per-canonical retirement clearance debt; no synthetic approvals.

The Git repository is archival storage, not evidence that an external consumer
was consulted. An unresolved historical release is never called cleared.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from retirement_integrity import verify_retirement_decisions

ROOT = Path(__file__).resolve().parents[2]


def audit(root: Path = ROOT) -> dict:
    history = json.loads((root / "architecture/retired-contract-releases.json").read_text())
    retired = set(history["retired"])
    verify_retirement_decisions(root, retired, history["reviews"])
    active = json.loads((root / "architecture/contract-consumers.json").read_text())
    active_paths = {x["path"] for x in active["active_releases"]}
    overlaps = sorted(active_paths & retired)
    if overlaps:
        raise ValueError("Active contracts cannot simultaneously be retired: " + repr(overlaps))
    records = []
    for path in sorted(retired):
        row = history["reviews"][path]
        external = row["external_consumer_review"]
        evidence = row.get("external_review_evidence")
        records.append({
            "path": path,
            "decision": row["decision"],
            "external_consumer_review": external,
            "clearance_status": "unresolved" if external == "not-independently-verified" else "recorded-approved",
            "internal_consumer_review": row["internal_consumer_review"],
            "evidence_url": evidence or None,
            "needs_external_inventory": external == "not-independently-verified",
            "needs_compatibility_disposition": external == "not-independently-verified",
            "needs_independent_approval": external == "not-independently-verified",
        })
    counts = Counter(x["clearance_status"] for x in records)
    return {
        "schema_version": 1,
        "description": "Historical removal review backlog; recorded approval requires separate GitHub provenance verification",
        "total_retirements": len(records),
        "unresolved": counts["unresolved"],
        "recorded_approved": counts["recorded-approved"],
        "can_claim_governance_closed": counts["unresolved"] == 0,
        "retirements": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-cleared", action="store_true")
    args = parser.parse_args()
    report = audit()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "total_retirements", "unresolved", "recorded_approved",
        "can_claim_governance_closed",
    )}))
    return 1 if args.require_cleared and not report["can_claim_governance_closed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
