"""Verify installed contracts in built OCI images or wheels, and bind owner APIs to the artifact.

The Dockerfile COPY, package-data declaration, source byte parity, and
canonical operation list do NOT establish built artifact contents. This reads
the actual immutable image filesystem or wheel ZIP and fails closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

from assurance import inventory

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = {
    "apps/console": ("console", "php"),
    "services/catalogue": ("catalogue", "php"),
    "services/governance": ("governance", "php"),
    "services/assurance": ("assurance", "php"),
    "services/inventory": ("inventory", "python"),
    "services/planning": ("planning", "python"),
    "services/lifecycle": ("lifecycle", "python"),
    "workers/inventory": ("inventory-workers", "python"),
    "workers/lifecycle": ("lifecycle-workers", "python"),
}


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def run(*argv: str) -> str:
    process = subprocess.run(argv, check=True, capture_output=True, text=True,
                             timeout=180)
    return process.stdout.strip()


def expected(component: str, root: Path = ROOT) -> tuple[list[dict], list[dict]]:
    if component not in COMPONENTS:
        raise ValueError(f"Unknown deployable component: {component}")
    registry = json.loads((root / "architecture/contract-consumers.json").read_text())
    owner = COMPONENTS[component][0]
    copies = [
        {"path": path, "canonical": release["path"], "sha256": sha((root / release["path"]).read_bytes())}
        for release in registry["active_releases"]
        for path in release.get("copies", [])
        if "/".join(Path(path).parts[:2]) == component
    ]
    contracts = inventory(root)
    operations = [
        {"key": op["key"], "release": op["release"],
         "release_sha256": op["release_sha256"], "operation_id": op["operation_id"]}
        for op in contracts["operations"] if op["owner"] == owner
    ]
    if not operations and owner not in {"console", "inventory-workers"}:
        raise ValueError(f"No registered owner operations for built component: {component}")
    return copies, operations


def check_wheel(component: str, wheel: Path, root: Path = ROOT) -> dict:
    if COMPONENTS[component][1] != "python":
        raise ValueError("Only a Python component may be bound to a wheel")
    copies, operations = expected(component, root)
    package = component.split("/")[-1].replace("-", "_")
    if component.startswith("workers/"):
        package = package + "_worker"
    with zipfile.ZipFile(wheel) as archive:
        members = set(archive.namelist())
        for item in copies:
            prefix = component + "/src/"
            if not item["path"].startswith(prefix):
                raise ValueError(f"Unexpected Python copy root: {item['path']}")
            packaged = item["path"][len(prefix):]
            if packaged not in members:
                raise ValueError(f"Wheel omits registered copy: {packaged}")
            if sha(archive.read(packaged)) != item["sha256"]:
                raise ValueError(f"Wheel has stale contract bytes: {packaged}")
        # A wheel must contain its actual code package, not just a contract JSON.
        if not any(name.startswith(package + "/") and name.endswith(".py")
                   for name in members):
            raise ValueError(f"Wheel has no executable package {package}")
        deployed = set()
        for name in members:
            if not name.startswith(package + "/") or not name.endswith(".json"):
                continue
            if any("/" + d + "/" in name for d in ("inputs", "contracts", "messaging")):
                deployed.add(name)
        registered = {item["path"].split("/src/", 1)[1] for item in copies}
        # Some components bundle application fixture JSON unrelated to contract
        # copies; only contract-bearing package directories are subject to parity.
        unregistered = deployed - registered
        if unregistered:
            raise ValueError(f"Wheel contains unregistered contract copies: {sorted(unregistered)}")
    return {
        "component": component, "owner": COMPONENTS[component][0],
        "kind": "wheel", "artifact_sha256": sha(wheel.read_bytes()),
        "source_revision": os.environ.get("GITHUB_SHA"),
        "installed_copies": copies, "owner_operations": operations,
    }


def check_image(component: str, tag: str, root: Path = ROOT) -> dict:
    copies, operations = expected(component, root)
    result = json.loads(run("docker", "image", "inspect", tag))
    if len(result) != 1:
        raise ValueError("OCI image must resolve to exactly one image")
    image = result[0]
    labels = image.get("Config", {}).get("Labels") or {}
    revision = os.environ.get("GITHUB_SHA")
    if not revision or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Cannot bind runtime image without exact 40-character Git SHA")
    if labels.get("org.opencontainers.image.revision") != revision:
        raise ValueError("Image source revision does not match actual CI checkout")
    image_id = image.get("Id", "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise ValueError("OCI image has no immutable content ID")
    cid = run("docker", "create", "--entrypoint", "/bin/true", tag)
    try:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            if COMPONENTS[component][1] == "php":
                app_root = "/app/resources/contracts"
                local_root = destination / "contracts"
            else:
                pkg = component.split("/")[-1].replace("-", "_")
                if component.startswith("workers/"):
                    pkg += "_worker"
                app_root = f"/opt/venv/lib/python3.12/site-packages/{pkg}"
                local_root = destination / pkg
            # docker cp works with created containers; application code is not run.
            # A directory may be absent for a component with no installed copies.
            if copies:
                run("docker", "cp", cid + ":" + app_root, str(local_root))
            for item in copies:
                if COMPONENTS[component][1] == "php":
                    packaged = local_root / Path(item["path"]).name
                else:
                    path = item["path"].split("/src/", 1)[1]
                    packaged = local_root / Path(*Path(path).parts[1:])
                if not packaged.is_file() or sha(packaged.read_bytes()) != item["sha256"]:
                    raise ValueError(f"Image missing/mismatched installed contract: {item['path']}")
            if COMPONENTS[component][1] == "php" and copies:
                actual = {p.name for p in local_root.glob("*.json")}
                expected_names = {Path(x["path"]).name for x in copies}
                if actual != expected_names:
                    raise ValueError(f"Image has orphan contract JSON: {sorted(actual ^ expected_names)}")
    finally:
        run("docker", "rm", cid)
    return {
        "component": component, "owner": COMPONENTS[component][0],
        "kind": "oci", "artifact_sha256": image_id.removeprefix("sha256:"),
        "source_revision": revision, "installed_copies": copies,
        "owner_operations": operations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--component", required=True, choices=COMPONENTS)
    selected = parser.add_mutually_exclusive_group(required=True)
    selected.add_argument("--wheel", type=Path)
    selected.add_argument("--image-tag")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    attestation = (check_wheel(args.component, args.wheel) if args.wheel
                   else check_image(args.component, args.image_tag))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(attestation, indent=2) + "\n")
    print(f"{args.component}: verified {len(attestation['installed_copies'])} image/wheel contracts, "
          f"{len(attestation['owner_operations'])} release-bound API operations")


if __name__ == "__main__":
    main()
