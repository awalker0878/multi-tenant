"""Reject executable references to canonical contracts retired from the working tree."""
from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Immutable Git-blob fingerprint of the 53 retirements that predate enforcement.
# This is an exception roster, NOT evidence that those consumers were cleared.
PRE_ENFORCEMENT_BLOB_SHA1 = "5a5ba6316d1b8d4148d20ec070d3f3afa01ab71c"
BASELINE = "architecture/retirement-unverified-baseline.txt"
CODE_SUFFIXES = {".py", ".php", ".ts", ".vue", ".sh", ".yml", ".yaml", ".toml"}
SKIP_DIRS = {"node_modules", "vendor", ".venv", "venv", "dist", "build", "__pycache__"}
SOURCE_FOLDERS = ("scripts", "tests", "apps", "services", "workers", ".github/workflows")


def verify_retirement_decisions(root: Path, retired: set[str], reviews: dict) -> None:
    """Preserve unresolved historical debt; fail closed for new retirements."""
    baseline = (root / BASELINE).read_bytes()
    header = b"blob " + str(len(baseline)).encode() + bytes([0])
    if hashlib.sha1(header + baseline).hexdigest() != PRE_ENFORCEMENT_BLOB_SHA1:
        raise ValueError("Previously unverified retirement roster was modified")
    frozen = set(baseline.decode("utf-8").splitlines())
    if not frozen <= retired:
        raise ValueError("Historical retirement record missing")
    if set(reviews) != retired:
        raise ValueError("Every retired contract requires its own review entry")
    clearances_file = root / "architecture/retirement-clearances.json"
    staged = (json.loads(clearances_file.read_text(encoding="utf-8"))
              if clearances_file.is_file()
              else {"schema_version": 1, "clearances": {}})
    if staged.get("schema_version") != 1 or not isinstance(staged.get("clearances"), dict):
        raise ValueError("Invalid staged external consumer clearance records")
    for path, review in reviews.items():
        if not isinstance(review, dict) or not all(
            isinstance(review.get(key), str) and review[key].strip()
            for key in ("reason", "internal_consumer_review", "external_consumer_review", "decision")
        ):
            raise ValueError(f"Retirement review incomplete: {path}")
        status = review["external_consumer_review"]
        if status == "not-independently-verified":
            if path not in frozen:
                raise ValueError(f"New retirement lacks external consumer clearance: {path}")
            continue
        if status not in {"verified_no_external_consumers", "verified_compatibility_commitments_satisfied"}:
            raise ValueError(f"Unsupported external consumer clearance: {path}")
        if (not isinstance(review.get("external_review_evidence"), str)
                or not review["external_review_evidence"].strip()
                or review.get("compatibility_commitments") not in {"none", "satisfied"}):
            raise ValueError(f"External consumer review evidence missing: {path}")
        approval = staged["clearances"].get(path)
        if (not isinstance(approval, dict) or approval.get("status") != "approved"
                or approval.get("decision") != "retire"
                or approval.get("consumer_inventory_evidence") != review["external_review_evidence"]
                or approval.get("compatibility_commitments") != review["compatibility_commitments"]):
            raise ValueError(f"Retirement lacks separately reviewed staged clearance: {path}")


def verify_retired_references(root: Path, retired: set[str]) -> None:
    """No active code, test, generator, or workflow may load a retired artifact."""
    patterns = {
        path: re.compile(r"(?<![A-Za-z0-9_.-])" + re.escape(Path(path).name)
                         + r"(?![A-Za-z0-9_.-])")
        for path in retired
    }
    failures: list[str] = []
    for folder in SOURCE_FOLDERS:
        source_root = root / folder
        if not source_root.exists():
            continue
        for source in source_root.rglob("*"):
            if (not source.is_file() or source.suffix not in CODE_SUFFIXES
                    or any(part in SKIP_DIRS for part in source.relative_to(root).parts)):
                continue
            text = source.read_text(encoding="utf-8")
            for number, line in enumerate(text.splitlines(), 1):
                for path, pattern in patterns.items():
                    if path in line or pattern.search(line):
                        failures.append(f"{source.relative_to(root)}:{number}: {path}")
    if failures:
        raise ValueError("Retired contracts still referenced by executable code: "
                         + "; ".join(failures[:30]))


if __name__ == "__main__":
    record = json.loads(
        (ROOT / "architecture/retired-contract-releases.json").read_text(encoding="utf-8")
    )
    retired = set(record["retired"])
    verify_retirement_decisions(ROOT, retired, record["reviews"])
    verify_retired_references(ROOT, retired)
    unresolved = sum(review["external_consumer_review"] == "not-independently-verified"
                     for review in record["reviews"].values())
    print(f"Retirement integrity: {len(retired)} retired paths, {unresolved} historical external reviews unresolved")
