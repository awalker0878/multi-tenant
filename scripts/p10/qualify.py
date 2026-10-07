"""Source-bound P10 E2 engineering campaign. A green run does not accept G10."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dossier import ROOT, freeze, reconcile
from evidence import canonical, decode, digest
from metrics import summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "evidence_level": "E2",
        "native_platforms_tested": [],
        "release_authorized": False,
        "native_write_authorized": False,
        "commands": [],
        "limitations": [
            "Real PostgreSQL/TLS with synthetic native owners; no installed tuple or receiving acceptance.",
            "Single Lifecycle database restore does not establish coordinated control-plane RPO/RTO.",
            "Synthetic scheduler load has no approved capacity or SLO claim.",
            "Local alert receiver is not an operational recipient or on-call handover.",
        ],
    }
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["P10_MEASUREMENTS_DIR"] = str(output / "measurements")
    env["P07_POSTGRES_BIN"] = env.get("P05_POSTGRES_BIN", "")

    def command(directory, argv):
        index = len(report["commands"])
        try:
            result = subprocess.run(
                argv,
                cwd=ROOT / directory,
                env=env,
                capture_output=True,
                text=True,
                timeout=1200,
                check=False,
            )
            code, data = result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired as error:
            code, data = 124, str(error)
        filename = f"{index:02d}.log"
        (output / filename).write_text(data)
        report["commands"].append(
            {
                "directory": directory,
                "argv": argv,
                "exit_code": code,
                "log": filename,
                "sha256": digest(data.encode()),
            }
        )
        print(
            f"{index:02d}: {'PASS' if code == 0 else 'FAIL'} {argv[0]} {directory}",
            flush=True,
        )
        if code:
            raise RuntimeError("command_failed:" + filename)

    try:
        if not env.get("P05_POSTGRES_BIN"):
            raise RuntimeError(
                "P05_POSTGRES_BIN required; skipped database cases cannot qualify"
            )
        candidate = freeze()
        report.update(
            source_revision=candidate["source_revision"],
            candidate_sha256=candidate["candidate_sha256"],
        )
        (output / "candidate.json").write_bytes(canonical(candidate) + b"\n")
        packet = decode((ROOT / "release/p10-inputs.json").read_bytes())
        dossier = reconcile(ROOT, candidate, packet)
        (output / "dossier.json").write_bytes(canonical(dossier) + b"\n")
        report["g10_status"] = dossier["status"]
        command(
            ".",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "scripts/p10",
                "-p",
                "test_*.py",
                "-v",
            ],
        )
        command(
            ".",
            [
                sys.executable,
                "scripts/p09/qualify.py",
                "--output",
                str(output / "components"),
            ],
        )
        components = json.loads((output / "components/report.json").read_bytes())
        if components["result"] != "PASSED" or any(
            s["skipped"] for s in components["suites"]
        ):
            raise RuntimeError("component_evidence_incomplete")
        report["component_suites"] = components["suites"]
        print("P10_SUITES=" + canonical(components["suites"]).decode(), flush=True)
        command("scripts/p01/contracts", ["uv", "sync", "--locked"])
        command(
            ".",
            [
                str(ROOT / "scripts/p01/contracts/.venv/bin/python"),
                "scripts/p07/check_native_contract.py",
            ],
        )
        command(
            ".",
            [
                str(ROOT / "services/planning/.venv/bin/python"),
                "scripts/p07/check_composition.py",
            ],
        )
        command(
            ".",
            [
                str(ROOT / "services/planning/.venv/bin/python"),
                "scripts/p08/check_composition.py",
            ],
        )
        tool_directory = output.parent / (output.name + "-tools")
        command(
            ".",
            [
                sys.executable,
                "scripts/p01/artifacts/tools.py",
                "--output",
                str(tool_directory),
            ],
        )
        env["P01_COSIGN"] = str(tool_directory / "cosign")
        command(
            ".",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "scripts/p01/artifacts",
                "-p",
                "test_*.py",
                "-q",
            ],
        )
        command(
            ".",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "scripts/p01",
                "-p",
                "test_*.py",
                "-q",
            ],
        )
        workload = json.loads((output / "measurements/scheduler.json").read_bytes())
        measurements = summarize(
            workload["records"],
            workload["tenants"],
            workload["start_ns"],
            workload["end_ns"],
        )
        (output / "measurements/summary.json").write_bytes(
            canonical(measurements) + b"\n"
        )
        report["measurement_summary"] = measurements
        print("P10_MEASUREMENTS=" + canonical(measurements).decode(), flush=True)
        print(
            "P10_RESTORE="
            + (output / "measurements/stale-restore.json").read_text().strip(),
            flush=True,
        )
        report["result"] = "PASSED_ENGINEERING_CHECKS"
    except (
        RuntimeError,
        ValueError,
        OSError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
    ) as error:
        report.update(result="FAILED", error=str(error))
    report["retained_sha256"] = {
        str(p.relative_to(output)): digest(p.read_bytes())
        for p in sorted(output.rglob("*"))
        if p.is_file() and p != output / "report.json"
    }
    (output / "report.json").write_bytes(canonical(report) + b"\n")
    print(
        json.dumps(
            {
                "result": report["result"],
                "g10_status": report.get("g10_status", "NOT_EVALUATED"),
                "release_authorized": False,
            }
        )
    )
    return 0 if report["result"] == "PASSED_ENGINEERING_CHECKS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
