#!/usr/bin/env python3
"""Verify original campaign evidence against its exact Git source and archive bytes."""

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "verification/p08/campaigns"


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@lru_cache(maxsize=None)
def source_sha(source, name):
    return sha(subprocess.check_output(["git", "show", source + ":" + name], cwd=ROOT))


def verify(screenshot_name="migration-campaign.png", console_expected=(7, 192, 911)):
    campaigns = []
    for item in json.loads((DEST / "manifest.json").read_text()):
        path = DEST / item["archive"]
        require(sha(path.read_bytes()) == item["archive_sha256"], str(path))
        with zipfile.ZipFile(path) as archive:
            raw = archive.read("report.json")
            report = json.loads(raw)
            source = report.get("source_revision", report.get("source_sha"))
            require(source == item["source_revision"], "source revision")
            bindings = report.get("source_bindings", report.get("source_sha256"))
            require(bool(bindings), "missing source bindings")
            for name, expected in bindings.items():
                require(source_sha(source, name) == expected, (path, name))
            for command in report["commands"]:
                if "log" in command:
                    require(
                        sha(archive.read(command["log"])) == command["sha256"], command
                    )
                else:
                    for stream in ("stdout", "stderr"):
                        require(
                            sha(archive.read(command[stream]))
                            == command[stream + "_sha256"],
                            command,
                        )
            for name, expected in report.get("artifact_sha256", {}).items():
                require(sha(archive.read(name)) == expected, (path, name))
            suites = []
            for suite in report.get("suites", []):
                xml = ElementTree.fromstring(archive.read(suite["name"] + ".xml"))
                totals = {
                    key: sum(int(s.get(key, 0)) for s in xml.iter("testsuite"))
                    for key in ("tests", "failures", "errors", "skipped")
                }
                require(suite == {"name": suite["name"], **totals}, suite)
                suites.append(suite)
            passed = report["result"] in ("PASSED", "PASS")
            if passed:
                require(
                    not report.get("error") and not report.get("failure"),
                    "reported error",
                )
                require(
                    all(
                        c.get("passed", c["exit_code"] == 0) for c in report["commands"]
                    ),
                    "command failure",
                )
                require(
                    all(c["passed"] for c in report.get("checks", [])), "check failure"
                )
                if item["kind"] == "components":
                    require(len(suites) == 5, "missing component suite")
                    require(
                        all(
                            s["tests"]
                            and not any(s[k] for k in ("failures", "errors", "skipped"))
                            for s in suites
                        ),
                        "incomplete component suite",
                    )
                if item["kind"] == "browser":
                    stats = report["stats"]
                    require(
                        stats["expected"] == 3
                        and not any(
                            stats[k] for k in ("unexpected", "flaky", "skipped")
                        ),
                        "incomplete browser journey",
                    )
                    screenshot = next(
                        n
                        for n in archive.namelist()
                        if n.endswith("/" + screenshot_name)
                    )
                    require(
                        (DEST / item.get("screenshot_file", screenshot_name)).read_bytes()
                        == archive.read(screenshot),
                        "screenshot mismatch",
                    )
            else:
                require(report["result"] in ("FAILED", "FAIL"), "unknown result")
                require(
                    any(
                        not c.get("passed", c["exit_code"] == 0)
                        for c in report["commands"]
                    ),
                    "missing original failure",
                )
            console_tests = None
            if item["kind"] == "console" and any(
                c["name"] == "pest" for c in report["commands"]
            ):
                command = next(c for c in report["commands"] if c["name"] == "pest")
                stdout = re.sub(
                    r"\x1b\[[0-9;]*m", "", archive.read(command["stdout"]).decode()
                )
                match = re.search(
                    r"Tests:\s+(\d+) skipped,\s+(\d+) passed\s+\((\d+) assertions\)",
                    stdout,
                )
                require(match is not None, "missing Console test summary")
                console_tests = dict(
                    zip(("skipped", "passed", "assertions"), map(int, match.groups()))
                )
                require(
                    console_tests
                    == dict(
                        zip(
                            ("skipped", "passed", "assertions"),
                            item.get("console_test_counts", console_expected),
                        )
                    ),
                    "unexpected Console test counts",
                )
            if item["kind"] == "console" and passed:
                require(console_tests is not None, "missing passing Console test run")
            output = DEST / "reports" / path.stem / "report.json"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(raw)
            campaigns.append(
                item
                | {
                    "result": report["result"],
                    "source_bindings_verified": len(bindings),
                    "commands": len(report["commands"]),
                    "suites": suites,
                    "stats": report.get("stats", report.get("browser_stats")),
                    "console_tests": console_tests,
                    "report": str(output.relative_to(DEST)),
                    "report_sha256": sha(raw),
                }
            )
    return {
        "schema_version": 1,
        "evidence_level": "E2",
        "campaigns": campaigns,
        "native_write_authorized": False,
        "native_platforms_tested": [],
        "limitations": [
            "Real PostgreSQL/TLS and Vue/Inertia browser; synthetic native and current-owner peers.",
            "Console's seven separate-broker-campaign skips remain skips.",
            "Account commissioning, complete native composition, physical measurements and Q07/G08 acceptance remain open.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=DEST)
    parser.add_argument("--screenshot", default="migration-campaign.png")
    parser.add_argument(
        "--console-counts",
        type=int,
        nargs=3,
        default=(7, 192, 911),
        metavar=("SKIPPED", "PASSED", "ASSERTIONS"),
    )
    args = parser.parse_args()
    DEST = args.directory.resolve()
    if not DEST.is_relative_to(ROOT / "verification/p08"):
        parser.error("Evidence directory must be within verification/p08")
    result = verify(args.screenshot, tuple(args.console_counts))
    (DEST / "qualification-index.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            [
                {
                    key: campaign[key]
                    for key in (
                        "kind",
                        "result",
                        "source_bindings_verified",
                        "commands",
                        "suites",
                        "stats",
                        "console_tests",
                    )
                }
                for campaign in result["campaigns"]
            ],
            indent=2,
        )
    )
