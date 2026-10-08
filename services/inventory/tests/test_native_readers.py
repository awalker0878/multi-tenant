"""An unattended native boundary can read only its commissioned confirmed review."""

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from inventory.domain.discovery import Rejected
from inventory.infrastructure.native_readers import native_reader


def setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[list[Any], dict[str, Any], Path]:
    grant: dict[str, Any] = {
        k: str(uuid4()) for k in ("tenant_id", "application_id", "environment", "site_id")
    }
    token = tmp_path / "read.token"
    token.write_text("a" * 64)
    grant.update(revision=1, digest="b" * 64)
    reader = {
        "reader_id": str(uuid4()),
        "token_file": str(token),
        "expires_at": 2000,
        "scopes": [grant],
    }
    path = tmp_path / "readers.json"
    config = {"schema_version": 1, "grants": [reader]}
    path.write_text(json.dumps(config))
    monkeypatch.setenv("INVENTORY_NATIVE_READERS_FILE", str(path))
    monkeypatch.setattr("inventory.infrastructure.native_readers.time.time", lambda: 1000)
    args = [
        "a" * 64,
        *[grant[k] for k in ("tenant_id", "application_id", "environment", "site_id")],
        1,
        "b" * 64,
    ]
    return args, config, path


@pytest.mark.parametrize("index", range(7))
def test_each_scope_dimension_and_credential_is_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, index: int
) -> None:
    args, _, _ = setup(tmp_path, monkeypatch)
    native_reader(*args)
    args[index] = 2 if index == 5 else "c" * 64 if index in {0, 6} else str(uuid4())
    with pytest.raises(Rejected):
        native_reader(*args)


@pytest.mark.parametrize(
    "fault",
    [
        "revoked",
        "expired",
        "duplicate",
        "symlink",
        "writable",
        "rotation",
        "boolean",
        "duplicate_json",
    ],
)
def test_unattended_read_grants_are_protected_and_revocable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    args, config, path = setup(tmp_path, monkeypatch)
    native_reader(*args)
    if fault == "revoked":
        config["grants"] = []
    elif fault == "expired":
        config["grants"][0]["expires_at"] = 1000
    elif fault == "duplicate":
        config["grants"].append(dict(config["grants"][0]))
    elif fault == "rotation":
        Path(config["grants"][0]["token_file"]).write_text("z" * 64)
    elif fault == "boolean":
        config["schema_version"] = True
    path.write_text(json.dumps(config))
    if fault == "symlink":
        link = tmp_path / "alias.json"
        link.symlink_to(path)
        monkeypatch.setenv("INVENTORY_NATIVE_READERS_FILE", str(link))
    elif fault == "writable":
        path.chmod(0o666)
    elif fault == "duplicate_json":
        path.write_text('{"schema_version":1,"schema_version":1,"grants":[]}')
    with pytest.raises(Rejected):
        native_reader(*args)


def test_one_reader_can_observe_multiple_exact_reviews(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    args, config, path = setup(tmp_path, monkeypatch)
    second = dict(config["grants"][0]["scopes"][0], revision=2, digest="c" * 64)
    config["grants"][0]["scopes"].append(second)
    path.write_text(json.dumps(config))
    native_reader(*args)
    native_reader(*(args[:5] + [2, "c" * 64]))
    with pytest.raises(Rejected):
        native_reader(*(args[:5] + [2, "b" * 64]))
