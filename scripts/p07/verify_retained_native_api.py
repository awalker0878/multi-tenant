"""Verify retained original archives against Git source and embedded digest bindings."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path
import subprocess
import zipfile
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "verification/p07/native-api"
QUALIFIED_SOURCE = "4ee67fdd704f6b6c401237137e3d8e2940ba3d1a"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=None)
def source_digest(source: str, path: str) -> str:
    return sha(subprocess.check_output(["git", "show", source + ":" + path], cwd=ROOT))


def verify() -> dict:
    campaigns = []
    for record in json.loads((DEST / "manifest.json").read_text()):
        archive = DEST / record["archive"]
        assert sha(archive.read_bytes()) == record["archive_sha256"], archive
        with zipfile.ZipFile(archive) as zipped:
            raw = zipped.read("report.json")
            report = json.loads(raw)
            source = report.get("source_revision", report.get("source_sha"))
            assert source == record["source_revision"], archive
            bindings = report.get(
                "source_bindings", report.get("source_sha256", report.get("input_sha256", {}))
            )
            assert bindings, archive
            mismatches = []
            for path, expected in bindings.items():
                actual = source_digest(source, path)
                if actual != expected:
                    mismatches.append({"path": path, "reported_sha256": expected, "git_sha256": actual})
            if source == QUALIFIED_SOURCE:
                assert not mismatches, (archive, mismatches)
            logs = 0
            for command in report["commands"]:
                pairs = [("log", "sha256"), ("stdout", "stdout_sha256"), ("stderr", "stderr_sha256")]
                if "name" in command and "log" not in command and "sha256" in command:
                    assert sha(zipped.read(command["name"] + ".log")) == command["sha256"]
                    logs += 1
                for path_key, hash_key in pairs:
                    if path_key in command:
                        assert sha(zipped.read(command[path_key])) == command[hash_key]
                        logs += 1
            artifacts = report.get("artifacts", report.get("artifact_sha256", {}))
            for path, expected in artifacts.items():
                assert sha(zipped.read(path)) == expected, (archive, path)
            suites = {}
            for path in zipped.namelist():
                if path.endswith(".xml"):
                    nodes = list(ET.fromstring(zipped.read(path)).iter("testsuite"))
                    suites[path] = {
                        key: sum(int(node.get(key, 0)) for node in nodes)
                        for key in ("tests", "failures", "errors", "skipped")
                    }
            if report["result"] in {"PASS", "PASSED"}:
                for command in report["commands"]:
                    allowed = command.get("expected_exit_codes", [command.get("expected_exit_code", 0)])
                    # Browser campaigns include deliberate failing broker/worker commands;
                    # their explicit outcome assertions are retained in checks and logs.
                    if "checks" not in report or "expected_exit_codes" in command or "expected_exit_code" in command:
                        assert command["exit_code"] in allowed, (archive, command)
                assert all(s[key] == 0 for s in suites.values() for key in ("failures", "errors"))
                if archive.name.startswith("p07-"):
                    assert all(s["skipped"] == 0 for s in suites.values()), archive
                assert all(c["passed"] for c in report.get("checks", [])), archive
            snapshot = DEST / "reports" / archive.stem
            snapshot.mkdir(parents=True, exist_ok=True)
            (snapshot / "report.json").write_bytes(raw)
            result = record | {
                "result": report["result"],
                "observed_at": report.get("observed_at"),
                "source_bindings_verified": len(bindings) - len(mismatches),
                "source_binding_mismatches": mismatches,
                "command_logs_verified": logs,
                "artifact_hashes_verified": len(artifacts),
                "nonzero_commands": [c for c in report["commands"] if c["exit_code"] != 0],
                "test_suites": suites,
                "report": str((snapshot / "report.json").relative_to(DEST)),
            }
            if "checks" in report:
                result["observed_checks"] = len(report["checks"])
            if "error" in report:
                result["original_error"] = report["error"]
            if "observations.json" in zipped.namelist():
                observed = zipped.read("observations.json")
                (snapshot / "observations.json").write_bytes(observed)
                observations = json.loads(observed)
                result["observed_checks"] = len(observations["checks"])
                result["replayed_histories"] = len(observations["histories"])
                assert all(c["result"] == "PASSED" for c in observations["checks"])
                assert all(h["replay"] == "PASSED" for h in observations["histories"])
                for path in zipped.namelist():
                    if path.startswith("history-") and path.endswith(".json"):
                        assert path in artifacts, path
                        (snapshot / path).write_bytes(zipped.read(path))
            campaigns.append(result)
    return {
        "schema_version": 1,
        "evidence_level": "E2",
        "source_revision": QUALIFIED_SOURCE,
        "scope": "Native API component, PostgreSQL, Temporal and dependent browser qualification.",
        "native_platforms_tested": [],
        "native_write_authorized": False,
        "production_native_dispatch_enabled": False,
        "campaigns": campaigns,
        "limitations": [
            "TLS peers use synthetic OpenStack/vSphere responses; no installed native platform is exercised.",
            "Actual PostgreSQL and Temporal exercise durable journals and dispatch with synthetic current owners and stage effects.",
            "The copy component covers parts of P08 M3/M4/M6, not snapshot/clone, OVF, conversion, guest transformation or delta cutover.",
            "Current-owner/caller-trust composition, native fencing and selected guest/service/traffic/retirement integrations remain unfinished.",
            "No Q05/Q06 native campaign, G07 receiving, operating acceptance or P07 completion is established.",
        ],
    }


if __name__ == "__main__":
    index = verify()
    (DEST / "qualification-index.json").write_text(json.dumps(index, indent=2) + "\n")
    print(json.dumps([{k: c[k] for k in ("archive", "result", "test_suites", "source_bindings_verified")}
                      for c in index["campaigns"]], indent=2))
