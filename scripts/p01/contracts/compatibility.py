"""Verify active immutability and every canonical deletion against Git, not the editable registry."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

AREAS = ("openapi", "schemas", "capabilities", "platforms", "asyncapi")
CLEARANCES = "architecture/retirement-clearances.json"


def compare(base: dict[str, bytes], head: dict[str, bytes]) -> list[str]:
    return sorted(path for path, value in base.items() if head.get(path) != value)


def is_published_contract(path: str) -> bool:
    parts = Path(path).parts
    return (len(parts) >= 3 and parts[0] == "contracts"
            and parts[1] in AREAS and ".." not in parts
            and Path(path).suffix in {".json", ".yaml", ".yml"})


def approved_clearance(path: str, approval: dict, baseline_sha256: str) -> None:
    """Admission shape only; underlying evidence and independent approval require human review."""
    if not isinstance(approval, dict):
        raise ValueError(f"Reviewed retirement clearance missing: {path}")
    required = ("status", "owner", "reviewed_by", "review_url", "reviewed_at",
                "consumer_inventory_evidence", "compatibility_evidence",
                "compatibility_commitments", "contract_sha256", "decision")
    if any(not isinstance(approval.get(k), str) or not approval[k].strip() for k in required):
        raise ValueError(f"Reviewed retirement clearance incomplete: {path}")
    if approval["status"] != "approved" or approval["decision"] != "retire":
        raise ValueError(f"Retirement clearance not approved: {path}")
    if approval["owner"] == approval["reviewed_by"]:
        raise ValueError(f"Retirement clearance lacks independent reviewer: {path}")
    if approval["contract_sha256"] != baseline_sha256:
        raise ValueError(f"Retirement evidence not bound to reviewed contract bytes: {path}")
    if approval["compatibility_commitments"] not in {"none", "satisfied"}:
        raise ValueError(f"Unresolved compatibility commitment: {path}")
    if (not isinstance(approval.get("assessed_consumers"), list)
            or any(not isinstance(v, str) or not v.strip()
                   for v in approval["assessed_consumers"])):
        raise ValueError(f"External consumer inventory not enumerated: {path}")
    for field in ("review_url", "consumer_inventory_evidence", "compatibility_evidence"):
        parsed = urlparse(approval[field])
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError(f"Invalid external evidence reference {field}: {path}")
    review = urlparse(approval["review_url"])
    if not (review.hostname == "github.com"
            and re.fullmatch(r"/[^/]+/[^/]+/pull/[1-9][0-9]*", review.path)):
        raise ValueError(f"Independent review requires a GitHub pull-request reference: {path}")
    try:
        if datetime.fromisoformat(approval["reviewed_at"].replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("naive")
    except ValueError as error:
        raise ValueError(f"Retirement review timestamp invalid: {path}") from error


def check(root: Path, base_revision: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", base_revision) or set(base_revision) == {"0"}:
        raise ValueError("An explicit existing base commit is required")

    def git(*args: str) -> bytes:
        try:
            return subprocess.run(["git", *args], cwd=root, check=True,
                                  capture_output=True, timeout=30).stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            raise ValueError("The review base Git commit must be available") from error

    git("cat-file", "-e", base_revision + "^{commit}")
    registry = json.loads((root / "architecture/contract-consumers.json").read_text())
    retirement = json.loads((root / "architecture/retired-contract-releases.json").read_text())
    active = {item["path"] for item in registry["active_releases"]}
    retired = set(retirement["retired"])
    if active & retired:
        raise ValueError("Active contract cannot be retired: " + ", ".join(sorted(active & retired)))
    if not all(map(is_published_contract, active | retired)):
        raise ValueError("Invalid canonical or retired contract path")

    # Critical: enumerate baseline contracts independently of CURRENT active registry.
    base_paths = set(filter(is_published_contract,
                           git("ls-tree", "-r", "--name-only", base_revision, "--", "contracts")
                           .decode().splitlines()))
    current = {
        str(p.relative_to(root)): p.read_bytes()
        for area in AREAS
        for p in (root / "contracts" / area).rglob("*")
        if p.is_file() and is_published_contract(str(p.relative_to(root)))
    }
    if set(current) != active:
        raise ValueError("Canonical inventory does not match active registry: "
                         + repr(sorted(set(current) ^ active)))
    missing = base_paths - set(current)
    unreviewed = missing - retired
    if unreviewed:
        raise ValueError("Canonical deleted without retirement record: " + ", ".join(sorted(unreviewed)))
    baseline = {path: git("show", base_revision + ":" + path)
                for path in sorted(base_paths & set(current))}
    conflicts = compare(baseline, current)
    if conflicts:
        raise ValueError("Active published contract removed or changed: " + ", ".join(conflicts))

    def base_json(path: str, default: dict) -> dict:
        present = git("ls-tree", "-r", "--name-only", base_revision, "--", path).decode().strip()
        return json.loads(git("show", base_revision + ":" + path)) if present == path else default

    prior_retired = set(base_json("architecture/retired-contract-releases.json", {"retired": []})["retired"])
    # These owner-directed removals predate the new two-stage review gate.
    # Their exact, pinned names remain an UNCLEARED backlog; no new deletion
    # may be smuggled into this exemption.
    frozen_file = root / "architecture/retirement-unverified-baseline.txt"
    frozen = set()
    if frozen_file.is_file():
        raw = frozen_file.read_bytes()
        git_blob = b"blob " + str(len(raw)).encode() + bytes([0]) + raw
        if hashlib.sha1(git_blob).hexdigest() != "5a5ba6316d1b8d4148d20ec070d3f3afa01ab71c":
            raise ValueError("Previously unverified retirement roster was modified")
        frozen = set(raw.decode("utf-8").splitlines())
        if not frozen <= retired:
            raise ValueError("Historical retirement record missing")
    new_retirements = retired - prior_retired - frozen
    clearance_file = root / CLEARANCES
    current_clearances = (json.loads(clearance_file.read_text()) if clearance_file.is_file()
                          else {"schema_version": 1, "clearances": {}})
    base_clearances = base_json(CLEARANCES, {"schema_version": 1, "clearances": {}})
    if current_clearances.get("schema_version") != 1 or not isinstance(current_clearances.get("clearances"), dict):
        raise ValueError("Invalid retirement clearance registry")
    if base_clearances.get("schema_version") != 1 or not isinstance(base_clearances.get("clearances"), dict):
        raise ValueError("Invalid review-base retirement clearance registry")

    for path in sorted(new_retirements | (missing - frozen)):
        # Pre-existing historical removals are tracked but do not masquerade as cleared.
        if path in prior_retired:
            continue
        approval = base_clearances["clearances"].get(path)
        if approval != current_clearances["clearances"].get(path):
            raise ValueError("Retirement clearance must be approved in an earlier reviewed base: " + path)
        if path not in base_paths:
            raise ValueError("Retirement must identify canonical in Git review base: " + path)
        approved_clearance(path, approval, hashlib.sha256(git("show", base_revision + ":" + path)).hexdigest())
        review = retirement.get("reviews", {}).get(path, {})
        if (review.get("external_consumer_review") not in
                {"verified_no_external_consumers", "verified_compatibility_commitments_satisfied"}
                or review.get("compatibility_commitments") != approval["compatibility_commitments"]
                or review.get("external_review_evidence") != approval["consumer_inventory_evidence"]):
            raise ValueError("Retirement manifest does not match independently staged clearance: " + path)

    return {
        "policy": "base-inventory-and-staged-retirement-clearance",
        "base_revision": base_revision,
        "checked_active_releases": len(active),
        "removed_from_review_base": sorted(missing),
        "staged_new_retirements": sorted(new_retirements),
        "baseline_sha256": {p: hashlib.sha256(v).hexdigest() for p, v in baseline.items()},
        "added": sorted(active - base_paths),
        "retired": sorted(retired),
        "conflicts": conflicts,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    args = parser.parse_args()
    print(json.dumps(check(Path(__file__).resolve().parents[3], args.base), indent=2))
