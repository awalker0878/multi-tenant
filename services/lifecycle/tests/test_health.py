"""Exercise the installed command rather than importing repository source."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def command(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "-m", "lifecycle.bootstrap.health", *arguments],
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
        cwd=Path(sys.prefix),
        env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
    )


def test_liveness_reports_only_process_bootstrap() -> None:
    result = command("liveness")
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["service"] == "lifecycle"
    assert payload["scope"] == "process_bootstrap"
    assert payload["probe"] == "liveness"
    assert payload["status"] == "ok"
    assert payload["native_operations_enabled"] is False


def test_readiness_cannot_succeed_before_dependencies_exist() -> None:
    result = command("readiness")
    assert result.returncode == 1, result.stderr
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["status"] == "not_ready"
    assert payload["reason"] == "service_dependencies_not_implemented"
    assert payload["native_operations_enabled"] is False


@pytest.mark.parametrize(
    "arguments",
    [(), ("ready",), ("liveness", "extra"), ("readiness", "--force"), ("--native",)],
)
def test_unsupported_input_fails_without_success_payload(arguments: tuple[str, ...]) -> None:
    result = command(*arguments)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "usage:" in result.stderr


def test_installed_console_entrypoint_matches_module() -> None:
    result = subprocess.run(
        [str(Path(sys.executable).parent / "lifecycle-health"), "liveness"],
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
        cwd=Path(sys.prefix),
        env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
    )
    module = command("liveness")
    assert result.returncode == module.returncode == 0
    assert result.stdout == module.stdout


def test_import_has_no_output_or_service_bootstrap() -> None:
    result = subprocess.run(
        [sys.executable, "-I", "-c", "import lifecycle"],
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
        cwd=Path(sys.prefix),
    )
    assert result.returncode == 0
    assert result.stdout == result.stderr == ""


def test_sibling_packages_are_absent_from_installed_environment() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import importlib.util; "
            "names = ['inventory', 'inventory_worker', 'lifecycle_worker', 'planning']; "
            "assert all(importlib.util.find_spec(name) is None for name in names)",
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
        cwd=Path(sys.prefix),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == result.stderr == ""
