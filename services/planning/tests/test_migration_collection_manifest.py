"""Real protected-file loader controls, never deployment enrollment evidence."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from planning.domain.model import digest
from planning.infrastructure.migration_collection_manifest import binding

RELEASE = "a" * 64
ROOT = Path(__file__).resolve().parents[3]


def documents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, dict[str, Any], dict[str, Any]]:
    manifest = json.loads(
        (ROOT / "contracts/capabilities/migration-collection-manifest-v1.json").read_text()
    )
    manifest_path = tmp_path / "manifest.json"
    registry_path = tmp_path / "registry.json"
    registry = {
        "schema_version": 1,
        "manifest_file": str(manifest_path),
        "manifest_sha256": digest(manifest),
        "releases": [RELEASE],
    }
    write(manifest_path, registry_path, manifest, registry)
    monkeypatch.setenv("PLANNING_MIGRATION_COLLECTION_REGISTRY_FILE", str(registry_path))
    return manifest_path, registry_path, manifest, registry


def write(
    manifest_path: Path, registry_path: Path, manifest: dict[str, Any], registry: dict[str, Any]
) -> None:
    manifest_path.write_text(json.dumps(manifest))
    registry_path.write_text(json.dumps(registry))
    manifest_path.chmod(0o600)
    registry_path.chmod(0o600)


def test_protected_loader_binds_exact_release_digest_and_every_scoped_attribute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, manifest, registry = documents(tmp_path, monkeypatch)
    result = binding(RELEASE)
    assert result is not None
    assert result["manifest_sha256"] == registry["manifest_sha256"]
    for platform, group in manifest["platforms"].items():
        for side in ("source", "target", "owner"):
            assert result["platforms"][platform][side] == sorted(
                row["id"] for row in group["attributes"] if row["scope"] == side
            )
    assert binding("b" * 64) is None


@pytest.mark.parametrize(
    "fault",
    [
        "registry_boolean",
        "manifest_boolean",
        "unknown_scope",
        "missing_scope",
        "duplicate",
        "invalid_id",
        "extra_platform",
        "digest",
        "writable_registry",
        "writable_manifest",
        "symlink",
        "relative",
        "unenrolled",
    ],
)
def test_malformed_or_unprotected_enrollment_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    mp, rp, manifest, registry = documents(tmp_path, monkeypatch)
    rows = manifest["platforms"]["vmware"]["attributes"]
    if fault == "registry_boolean":
        registry["schema_version"] = True
    elif fault == "manifest_boolean":
        manifest["schema_version"] = True
    elif fault == "unknown_scope":
        rows[0]["scope"] = "unrecognized"
    elif fault == "missing_scope":
        manifest["platforms"]["vmware"]["attributes"] = [
            row for row in rows if row["scope"] != "owner"
        ]
    elif fault == "duplicate":
        rows.append(deepcopy(rows[0]))
    elif fault == "invalid_id":
        rows[0]["id"] = ""
    elif fault == "extra_platform":
        manifest["platforms"]["unknown"] = deepcopy(manifest["platforms"]["vmware"])
    elif fault == "relative":
        registry["manifest_file"] = "manifest.json"
    elif fault == "unenrolled":
        registry["releases"] = ["b" * 64]
    registry["manifest_sha256"] = digest(manifest) if fault != "digest" else "c" * 64
    write(mp, rp, manifest, registry)
    if fault == "writable_registry":
        rp.chmod(0o666)
    elif fault == "writable_manifest":
        mp.chmod(0o666)
    elif fault == "symlink":
        link = tmp_path / "link.json"
        link.symlink_to(mp)
        registry["manifest_file"] = str(link)
        rp.write_text(json.dumps(registry))
    assert binding(RELEASE) is None


def test_missing_registry_does_not_inherit_canonical_requirements_as_enrollment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PLANNING_MIGRATION_COLLECTION_REGISTRY_FILE", raising=False)
    assert binding(RELEASE) is None
