"""Enforce the current, active-only canonical release inventory against Git.

This fresh-deployment tree contains no runtime compatibility aliases or retired
contract records. A published surviving release remains byte-immutable and every
installed copy must be declared in the current registry; the current contract
integrity tests check actual copy loaders independently.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

AREAS = ("openapi", "schemas", "capabilities", "platforms", "asyncapi")


def is_published_contract(path: str) -> bool:
    parts = Path(path).parts
    return (len(parts) >= 3 and parts[0] == "contracts"
            and parts[1] in AREAS and ".." not in parts
            and Path(path).suffix in {".json", ".yaml", ".yml"})


def compare(base: dict[str, bytes], head: dict[str, bytes]) -> list[str]:
    return sorted(path for path, value in base.items() if head.get(path) != value)


def check(root: Path, base_revision: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", base_revision) or set(base_revision) == {"0"}:
        raise ValueError("An explicit existing base commit is required")

    def git(*arguments: str) -> bytes:
        try:
            return subprocess.run(["git", *arguments], cwd=root, check=True,
                                  capture_output=True, timeout=30).stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            raise ValueError("The review base Git commit must be available") from error

    git("cat-file", "-e", base_revision + "^{commit}")
    release_registry = json.loads((root / "architecture/contract-consumers.json").read_text())
    active = {row["path"] for row in release_registry["active_releases"]}
    if not all(map(is_published_contract, active)):
        raise ValueError("Invalid active canonical contract path")
    current = {
        str(path.relative_to(root)): path.read_bytes()
        for area in AREAS
        for path in (root / "contracts" / area).rglob("*")
        if path.is_file() and is_published_contract(str(path.relative_to(root)))
    }
    if set(current) != active:
        raise ValueError("Canonical inventory does not match active registry: "
                         + repr(sorted(set(current) ^ active)))

    previous = set(filter(
        is_published_contract,
        git("ls-tree", "-r", "--name-only", base_revision, "--", "contracts")
        .decode().splitlines(),
    ))
    common = sorted(active & previous)
    baseline = {path: git("show", base_revision + ":" + path) for path in common}
    modified = compare(baseline, current)
    if modified:
        raise ValueError("Active published contract removed or changed: "
                         + ", ".join(modified))

    # Retirement must be justified against the *previous* consumer graph, not
    # merely by deleting both a release and its declarations in this change.
    removed = previous - active
    if removed:
        try:
            old_registry = json.loads(git("show", base_revision + ":architecture/contract-consumers.json"))
        except (ValueError, json.JSONDecodeError) as error:
            raise ValueError("Cannot establish previous contract consumers for retirement") from error
        old_releases = {item["path"]: item for item in old_registry.get("active_releases", [])}
        old_usage = {}
        try:
            old_usage = json.loads(git("show", base_revision + ":architecture/installed-contract-usage.json"))
        except ValueError as error:
            raise ValueError("Cannot establish previous installed contract usage for retirement") from error
        references = {}
        for item in old_registry.get("active_releases", []):
            for dependency in item.get("depends_on", []):
                references.setdefault(dependency, []).append(item["path"])
        for path in sorted(removed):
            item = old_releases.get(path)
            if item is None:
                raise ValueError("Unregistered prior canonical release cannot be retired: " + path)
            blockers = []
            if item.get("consumers"):
                blockers.append("declared consumers " + repr(item["consumers"]))
            if item.get("copies"):
                blockers.append("installed copies " + repr(item["copies"]))
            if references.get(path):
                blockers.append("dependent releases " + repr(references[path]))
            if any(row.get("canonical") == path for row in old_usage.get("copies", [])):
                blockers.append("runtime loader registrations")
            if blockers:
                raise ValueError("Contract retirement requires verified consumer removal: "
                                 + path + ": " + "; ".join(blockers))

    # A canonical deletion is permitted only as an actual worktree removal:
    # check_registry and runtime_inventory separately prohibit stale shipped
    # copies, undeclared source files, and dynamically loaded alias contracts.
    return {
        "policy": "active-only-immutable-canonical",
        "base_revision": base_revision,
        "checked_active_releases": len(active),
        "modified_existing": modified,
        "added": sorted(active - previous),
        "removed": sorted(previous - active),
        "baseline_sha256": {p: hashlib.sha256(v).hexdigest() for p, v in baseline.items()},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    args = parser.parse_args()
    print(json.dumps(check(Path(__file__).resolve().parents[3], args.base), indent=2))
