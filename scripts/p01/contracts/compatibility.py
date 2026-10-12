"""Check immutability of active canonical contracts against a review base commit."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def compare(base: dict[str, bytes], head: dict[str, bytes]) -> list[str]:
    """An existing active release is frozen byte-for-byte."""
    return sorted(path for path, value in base.items() if head.get(path) != value)


def is_published_contract(path: str) -> bool:
    return (path.startswith("contracts/")
            and ".." not in Path(path).parts
            and not path.startswith(("contracts/source/", "contracts/fixtures/"))
            and Path(path).suffix in {".json", ".yaml", ".yml"})


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
    current = {}
    for path in sorted(active):
        file = root / path
        if not file.is_file():
            raise ValueError("Active canonical missing: " + path)
        current[path] = file.read_bytes()
    base_paths = set(git("ls-tree", "-r", "--name-only", base_revision, "--", "contracts").decode().splitlines())
    baseline = {path: git("show", base_revision + ":" + path)
                for path in sorted(active & base_paths)}
    conflicts = compare(baseline, current)
    if conflicts:
        raise ValueError("Active published contract removed or changed: " + ", ".join(conflicts))
    return {
        "policy": "active-canonical-immutability",
        "base_revision": base_revision,
        "baseline": "review-base-commit",
        "checked_active_releases": len(active),
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
