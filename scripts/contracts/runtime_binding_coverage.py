"""Guarantee every deployable owner and installed copy has a built-artifact CI job."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from artifact_attestation import COMPONENTS
from installed_usage import verify_installed_usage
from assurance import inventory

ROOT = Path(__file__).resolve().parents[2]


def verify_required_ci_gate(root: Path) -> None:
    """Reject a disconnected or optional artifact gate, even if the builder exists."""
    ci = yaml.safe_load((root / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    jobs = ci.get("jobs", {}) if isinstance(ci, dict) else {}
    caller = jobs.get("artifact-binding-assurance", {})
    if (caller.get("uses") != "./.github/workflows/qualification.yml"
            or caller.get("with", {}).get("suite") != "contract-artifacts"
            or "scope" not in caller.get("needs", [])):
        raise ValueError("CI does not invoke source-pinned contract artifact qualification")
    # The required result must depend on an actual executed, strict
    # qualification job. A job name alone (or a report without
    # --require-qualified) is not a measured security release gate.
    assurance = jobs.get("contract-assurance", {})
    prerequisite = assurance.get("needs", [])
    if (not {"scope", "contracts", "laravel-routes"}.issubset(set(prerequisite))
            or "always()" not in str(assurance.get("if", ""))
            or "--require-qualified" not in str(assurance.get("steps", []))
            or "scripts/contracts/combine_assurance.py" not in str(assurance.get("steps", []))):
        raise ValueError("CI contract assurance does not enforce complete measured qualification")
    required = jobs.get("required", {})
    if ("artifact-binding-assurance" not in required.get("needs", [])
            or "contract-assurance" not in required.get("needs", [])
            or "scripts/ci/check.py" not in str(required.get("steps", []))):
        raise ValueError("Required CI does not enforce contract and artifact qualification")


def verify(root: Path = ROOT) -> dict:
    registry = json.loads((root / "architecture/contract-consumers.json").read_text())
    active = inventory(root)
    verify_installed_usage(root, registry)
    owner_components = {owner for owner, _ in COMPONENTS.values()}
    owners = {release["owner"] for release in registry["active_releases"]}
    unknown = owners - owner_components - {"contract-platform"}
    if unknown:
        raise ValueError(f"No built runtime component for contract owner: {sorted(unknown)}")
    copied_components = {
        "/".join(Path(copy).parts[:2])
        for release in registry["active_releases"]
        for copy in release.get("copies", [])
    }
    unmapped = copied_components - set(COMPONENTS)
    if unmapped:
        raise ValueError(f"Shipped contract component not mapped to built image: {sorted(unmapped)}")
    file = root / ".github/workflows/qualification.yml"
    workflow = yaml.safe_load(file.read_text(encoding="utf-8"))
    # A declared matrix is not a built-artifact guarantee. Fail closed if the
    # workflow stops building images, verifying wheel contents, or aggregating
    # the actual attestation artifacts.
    jobs = workflow["jobs"]
    artifact = jobs["artifact-bindings"]
    aggregate = jobs["aggregate-bindings"]
    if "artifact-bindings" not in aggregate.get("needs", []):
        raise ValueError("Runtime release aggregation must depend on built artifacts")
    def has_command(job: dict, fragment: str) -> bool:
        return any(fragment in str(step.get("run", "")) for step in job.get("steps", []))
    for command in ("docker build ", "artifact_attestation.py --component",
                    "pip wheel ", "runtime_binding_coverage.py"):
        if not has_command(artifact, command):
            raise ValueError("Artifact CI does not execute required build/verification: " + command)
    if not has_command(aggregate, "aggregate_artifacts.py --input-directory"):
        raise ValueError("Artifact CI does not aggregate measured built releases")
    verify_required_ci_gate(root)
    if not any("actions/download-artifact@" in str(step.get("uses", ""))
               for step in aggregate.get("steps", [])):
        raise ValueError("Artifact aggregation does not download the actual built evidence")
    matrix = artifact["strategy"]["matrix"]["include"]
    declared = [entry["component"] for entry in matrix]
    if len(declared) != len(set(declared)) or set(declared) != set(COMPONENTS):
        raise ValueError("Artifact CI omits/adds or duplicates a deployable contract owner")
    for entry in matrix:
        component = entry["component"]
        expected_python = COMPONENTS[component][1] == "python"
        if entry["python"] is not expected_python:
            raise ValueError(f"Wrong artifact type in CI: {component}")
        if not (root / component / "Dockerfile").is_file():
            raise ValueError(f"No Dockerfile for registered runtime owner: {component}")
        if expected_python and not (root / component / "pyproject.toml").is_file():
            raise ValueError(f"No Python wheel project for registered runtime owner: {component}")
    return {
        "components": len(declared),
        "owners": len(owners),
        "bound_http_operations": len(active["operations"]),
        "installed_components": len(copied_components),
        "unmapped_owner_operations": [
            operation["key"] for operation in active["operations"]
            if operation["owner"] not in owner_components
            and operation["owner"] != "contract-platform"
        ],
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
