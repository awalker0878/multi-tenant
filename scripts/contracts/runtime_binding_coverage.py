"""Guarantee every deployable owner and installed copy has a built-artifact CI job."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from artifact_attestation import COMPONENTS
from assurance import inventory

ROOT = Path(__file__).resolve().parents[2]


def verify(root: Path = ROOT) -> dict:
    registry = json.loads((root / "architecture/contract-consumers.json").read_text())
    active = inventory(root)
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
    matrix = workflow["jobs"]["artifact-bindings"]["strategy"]["matrix"]["include"]
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
