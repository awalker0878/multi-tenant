"""Run real Import Linter against independently copied, deliberately bad sources."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent
CASES: dict[str, tuple[str, str, str, str]] = {
    "domain-to-application": (
        "probe_inventory/domain/violation.py",
        "from ..application.advance import advance as aliased_advance\n",
        "Owned Python layer direction",
        "probe_inventory.domain.violation",
    ),
    "application-to-infrastructure": (
        "probe_inventory/application/violation.py",
        "from probe_inventory.infrastructure.memory import MemoryStore as Store\n",
        "Owned Python layer direction",
        "probe_inventory.application.violation",
    ),
    "interfaces-to-infrastructure": (
        "probe_inventory/interfaces/violation.py",
        "from ..infrastructure.memory import MemoryStore\n",
        "Owned Python layer direction",
        "probe_inventory.interfaces.violation",
    ),
    "private-service-import": (
        "probe_planning/application/violation.py",
        "from probe_inventory.domain.sample import Sample as ForeignSample\n",
        "Independent service sources",
        "probe_planning.application.violation",
    ),
    "domain-transport-import": (
        "probe_inventory/domain/violation.py",
        "import httpx as transport\n",
        "No transport libraries in core",
        "probe_inventory.domain.violation",
    ),
    "application-transport-model": (
        "probe_inventory/application/violation.py",
        "from pydantic import BaseModel as TransportModel\n",
        "No transport libraries in core",
        "probe_inventory.application.violation",
    ),
    "undeclared-layer": (
        "probe_inventory/unclassified.py",
        "VALUE = 1\n",
        "Owned Python layer direction",
        "probe_inventory.unclassified",
    ),
}


def check_case(name: str) -> dict[str, object]:
    path, content, rule, diagnostic = CASES[name]
    with TemporaryDirectory(prefix="p00-python-boundary-") as temporary:
        work = Path(temporary)
        shutil.copytree(ROOT / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copyfile(ROOT / ".importlinter", work / ".importlinter")
        (work / "src" / path).write_text(content)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(work / "src")
        command = [
            str(Path(sys.executable).parent / "lint-imports"),
            "--config",
            ".importlinter",
            "--no-cache",
            "--no-logo",
        ]
        result = subprocess.run(
            command, cwd=work, env=env, capture_output=True, text=True, timeout=30, check=False
        )
        output = result.stdout + result.stderr
        # A crash, bad invocation, absent module, or unrelated rule failure is not a pass.
        expected = result.returncode == 1 and f"{rule} BROKEN" in output and diagnostic in output
        return {
            "case": name,
            "injected_path": path,
            "injected_source": content,
            "expected_rule": rule,
            "expected_diagnostic": diagnostic,
            "exit_code": result.returncode,
            "outcome": "EXPECTED_REJECTION" if expected else "UNEXPECTED_RESULT",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }


def main() -> int:
    cases = [check_case(name) for name in CASES]
    success = all(case["outcome"] == "EXPECTED_REJECTION" for case in cases)
    print(json.dumps({"result": "PASS" if success else "FAIL", "cases": cases}, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
