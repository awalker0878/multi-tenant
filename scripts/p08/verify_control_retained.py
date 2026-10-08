#!/usr/bin/env python3
"""Verify native-control component/browser and unchanged Governance owner evidence."""

import json
import re
import subprocess
import zipfile

import verify_campaign_retained as campaigns


def main():
    root = campaigns.ROOT
    dest = root / "verification/p08/control"
    campaigns.DEST = dest
    result = campaigns.verify("migration-fleet.png")
    total = sum(s["tests"] for c in result["campaigns"] for s in c["suites"])
    campaigns.require(total == 951, "component count changed")
    manifest = json.loads((dest / "governance-manifest.json").read_text())
    archive_path = dest / manifest["archive"]
    campaigns.require(
        campaigns.sha(archive_path.read_bytes()) == manifest["archive_sha256"],
        "Governance archive changed",
    )
    with zipfile.ZipFile(archive_path) as archive:
        raw = archive.read("report.json")
        report = json.loads(raw)
        campaigns.require(report["source_sha"] == manifest["source_revision"], "Governance source")
        campaigns.require(report["run_id"] == manifest["run_id"], "Governance run")
        campaigns.require(report["result"] == "PASS", "Governance failed")
        campaigns.require(all(c["passed"] for c in report["checks"]), "Governance checks")
        for name, expected in report["source_sha256"].items():
            campaigns.require(campaigns.source_sha(report["source_sha"], name) == expected, name)
        for name, expected in report["artifact_sha256"].items():
            campaigns.require(campaigns.sha(archive.read(name)) == expected, name)
        text = re.sub(r"\x1b\[[0-9;]*m", "", archive.read("postgres-features.log").decode())
        match = re.search(r"Tests:\s+(\d+) passed \((\d+) assertions\)", text)
        campaigns.require(match is not None, "Governance test summary missing")
        counts = tuple(map(int, match.groups()))
        campaigns.require(counts == (219, 5919), "Governance test counts changed")
        stats = report["browser_stats"]
        campaigns.require(stats["expected"] == 2 and not any(
            stats[k] for k in ("skipped", "unexpected", "flaky")
        ), "Governance browser incomplete")
    final_source = result["campaigns"][0]["source_revision"]
    for path in ("services/governance", "contracts/openapi/governance-native-approval-v1.json"):
        revisions = [subprocess.check_output(
            ["git", "rev-parse", revision + ":" + path], cwd=root
        ) for revision in (report["source_sha"], final_source)]
        campaigns.require(revisions[0] == revisions[1], "Governance source changed: " + path)
    output = dest / "reports/governance/report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    result["governance"] = manifest | {
        "result": report["result"], "checks": len(report["checks"]),
        "source_bindings_verified": len(report["source_sha256"]),
        "artifacts_verified": len(report["artifact_sha256"]),
        "tests": counts[0], "assertions": counts[1],
        "browser_stats": stats, "report": "reports/governance/report.json",
        "report_sha256": campaigns.sha(raw), "unchanged_at_source": final_source,
    }
    correction = json.loads((dest / "correction.json").read_text())
    campaigns.require(campaigns.sha((dest / correction["log"]).read_bytes()) == correction["log_sha256"],
                      "Original architecture failure changed")
    result["correction"] = correction
    result["limitations"] = [
        "Real PostgreSQL, TLS and browsers; synthetic native platforms and custody/observation peers.",
        "Governance evidence has a separate exact source; its service tree and native contract are unchanged at the final component source.",
        "Provider custody/fencing, owner-specific guest/data/service/recovery implementations, interrupted-transfer reconciliation and physical measurements remain open.",
        "No native Q05/Q06/Q07, G07/G08 receiving or operating acceptance.",
    ]
    (dest / "qualification-index.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Verified 951 component tests, three migration browser journeys, 219 Governance tests and original correction evidence.")


if __name__ == "__main__":
    main()
