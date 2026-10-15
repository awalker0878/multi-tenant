"""Admit actual successful journey wire measurements as producer proof only."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from assurance import ROOT, inventory, operation_key


def producers(folder: Path, existing: list[dict], root: Path = ROOT) -> list[dict]:
    operations = {row["key"]: row for row in inventory(root)["operations"]}
    proved = {row["key"] for row in existing if row.get("claim") == "producer"}
    evidence = []
    expected = {"revision": os.environ.get("GITHUB_SHA"),
                "run_id": os.environ.get("GITHUB_RUN_ID"),
                "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT")}
    if not all(expected.values()):
        raise ValueError("Current journey CI provenance is required")
    validator = "scripts/contracts/route_conformance.py"
    validator_hash = hashlib.sha256((root / validator).read_bytes()).hexdigest()
    for wire in sorted(folder.rglob("http-conformance.json")):
        report = json.loads((wire.parent / "report.json").read_text())
        if any(report.get(name) != expected[name] for name in ("run_id", "run_attempt")) or (
            report.get("source_revision") != expected["revision"]
        ):
            raise ValueError("Stale journey run or source provenance")
        # A partly completed journey remains diagnostic. No global success is
        # inferred from a valid individual response in a failing campaign.
        if report.get("result") != "PASS" or report.get("source_unchanged") is not True:
            continue
        if (report.get("source_sha256", {}).get(validator) != validator_hash
                or report.get("artifact_sha256", {}).get(wire.name)
                != hashlib.sha256(wire.read_bytes()).hexdigest()):
            raise ValueError("Journey validator or measured wire bytes differ")
        rows = json.loads(wire.read_text())
        if not isinstance(rows, list):
            raise ValueError("Malformed journey measurements")
        for row in rows:
            if any(row.get(name) != value for name, value in expected.items()):
                raise ValueError("Stale journey measurement provenance")
            if row.get("positive_conformance") is not True:
                continue
            key = operation_key(row["owner"], row["method"], row["path"])
            operation = operations.get(key)
            if (operation is None or row.get("release") != operation["release"]
                    or row.get("release_sha256") != operation["release_sha256"]
                    or row.get("operation_id") != operation["operation_id"]):
                raise ValueError("Journey operation or canonical release differs")
            status = row.get("status_code")
            if (type(status) is not int or not 200 <= status < 300
                    or (str(status) not in operation["response_statuses"]
                        and "default" not in operation["response_statuses"])
                    or row.get("request_valid") is not True
                    or row.get("response_valid") is not True
                    or row.get("test") not in {
                        "scripts/p05/verify_live.py:wire", "scripts/p06/verify_live.py:wire"}
                    or not isinstance(row.get("response_sha256"), str)
                    or re.fullmatch(r"[0-9a-f]{64}", row["response_sha256"]) is None):
                raise ValueError("Journey lacks an independently validated positive response")
            # Repeated browser observations do not replace independently
            # executed consumer/security tests or fabricate image provenance.
            if key not in proved:
                evidence.append({"key": key, "claim": "producer", "source": "live-producer",
                                 "result": "PASS", "release_sha256": row["release_sha256"],
                                 "test": row["test"], "status_code": status,
                                 "response_sha256": row["response_sha256"], **expected})
                proved.add(key)
    return evidence
