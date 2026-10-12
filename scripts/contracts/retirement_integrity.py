"""Reject executable references to canonical contracts retired from the working tree."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE_SUFFIXES = {".py", ".php", ".ts", ".vue", ".sh", ".yml", ".yaml", ".toml"}
SKIP_DIRS = {"node_modules", "vendor", ".venv", "venv", "dist", "build", "__pycache__"}
SOURCE_FOLDERS = ("scripts", "tests", "apps", "services", "workers", ".github/workflows")


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
                if (source.relative_to(root).as_posix() == "tests/contracts/test_integrity.py"
                        and 'retired_path = "contracts/openapi/governance-native-approval-v1.json"' in line):
                    continue  # Deliberate negative canary: assert retired files cannot reappear.
                for path, pattern in patterns.items():
                    if path in line or pattern.search(line):
                        failures.append(f"{source.relative_to(root)}:{number}: {path}")
    if failures:
        raise ValueError("Retired contracts still referenced by executable code: "
                         + "; ".join(failures[:30]))


if __name__ == "__main__":
    retired = set(json.loads(
        (ROOT / "architecture/retired-contract-releases.json").read_text(encoding="utf-8")
    )["retired"])
    verify_retired_references(ROOT, retired)
    print(f"Retirement integrity: {len(retired)} paths have no executable references")
