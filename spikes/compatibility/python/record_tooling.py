"""Preserve a Python tooling command, exact input hashes, and its actual outcome."""

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT.parent / "results" / "python-tooling"
EXCLUDED = {
    ".venv",
    "__pycache__",
    ".ruff_cache",
    ".mypy_cache",
    ".pytest_cache",
    ".import_linter_cache",
}


def inputs() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(ROOT.rglob("*"))
        if path.is_file() and not EXCLUDED.intersection(path.relative_to(ROOT).parts)
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.name.replace("-", "").isalnum() or args.name != args.name.lower():
        parser.error("Use a lowercase alphanumeric and hyphen name")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("A command is required")
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"{args.name}.json"
    # Reserve the evidence name before execution; never replace an earlier attempt.
    with path.open("x") as handle:
        result: dict[str, object] = {
            "schema_version": 1,
            "cwd": "spikes/compatibility/python",
            "started_at": datetime.now(UTC).isoformat(),
            "command": command,
            "input_sha256": inputs(),
        }
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            result.update(
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                outcome="PASS" if completed.returncode == 0 else "FAIL",
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as error:
            result.update(exit_code=None, outcome="UNAVAILABLE_OR_TIMEOUT", stderr=str(error))
        result["finished_at"] = datetime.now(UTC).isoformat()
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"record": str(path), "outcome": result["outcome"]}))
    return 0 if result["outcome"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
