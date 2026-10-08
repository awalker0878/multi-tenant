"""Capture one reproducible spike command; preserve failures and input identities."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
EXCLUDED = {"node_modules", "vendor", ".venv", "__pycache__", ".cache", "results", "public"}


def inputs() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(ROOT.rglob("*"))
        if path.is_file() and not any(part in EXCLUDED for part in path.relative_to(ROOT).parts)
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Unique result name; existing records cannot be replaced")
    parser.add_argument("--cwd", choices=[".", "frontend", "php", "python"], default=".")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.name):
        parser.error("Use a lowercase alphanumeric and hyphen result name")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("A command is required after --")
    result_path = ROOT / "results" / f"{args.name}.json"
    if result_path.exists():
        parser.error("Result exists; use a new name to retain earlier evidence")
    result = {"schema_version": 1, "started_at": datetime.now(timezone.utc).isoformat(), "cwd": args.cwd, "command": command, "input_sha256": inputs()}
    try:
        completed = subprocess.run(command, cwd=ROOT / args.cwd, capture_output=True, text=True, timeout=args.timeout, check=False)
        result.update(exit_code=completed.returncode, stdout=completed.stdout, stderr=completed.stderr, outcome="PASS" if completed.returncode == 0 else "FAIL")
    except FileNotFoundError as error:
        result.update(exit_code=None, stdout="", stderr=str(error), outcome="UNAVAILABLE")
    except subprocess.TimeoutExpired as error:
        result.update(exit_code=None, stdout=(error.stdout or b"").decode() if isinstance(error.stdout, bytes) else error.stdout or "", stderr=(error.stderr or b"").decode() if isinstance(error.stderr, bytes) else error.stderr or "", outcome="TIMEOUT")
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    result_path.parent.mkdir(exist_ok=True)
    with result_path.open("x") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
    print(json.dumps({"record": str(result_path.relative_to(ROOT)), "outcome": result["outcome"], "exit_code": result["exit_code"]}))
    return 0 if result["outcome"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
