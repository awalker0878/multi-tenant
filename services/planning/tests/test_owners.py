"""Owned policy files must be bounded and protected before any remote read."""

import hashlib
import json
import os
from pathlib import Path
from unittest.mock import Mock

import pytest
from planning_fixture import ACTOR, APP, ENDPOINT, ENV, GENERATION, REVISION, SITE, TENANT

from planning.domain.model import Actor, Rejected
from planning.infrastructure.owners import OwnerSources


def test_protected_registry_resolves_exact_scoped_owner_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from planning_fixture import inputs

    intent, destination, profile, policy, qualification = inputs()
    registry = {
        "schema_version": 1,
        "assignments": [
            {
                "tenant_id": TENANT,
                "site_id": SITE,
                "endpoint_id": ENDPOINT,
                "profile": "selected",
                "policy": "selected",
            }
        ],
        "profiles": {
            "selected": {
                "platform": profile["platform"],
                "version": profile["version"],
                "declarations": {
                    row["dimension"]: row["declaration"] for row in profile["dimensions"]
                },
            }
        },
        "policies": {"selected": policy},
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry))
    path.chmod(0o640)
    monkeypatch.setenv("PLANNING_REGISTRY_FILE", str(path))
    catalogue = {
        "id": REVISION,
        "application_id": APP,
        "intent": intent,
        "digest": hashlib.sha256(
            json.dumps(intent, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest(),
    }
    owner_read = Mock(side_effect=[catalogue, destination, qualification])
    monkeypatch.setattr("planning.infrastructure.owners.request", owner_read)
    result, rows = OwnerSources().resolve(
        Actor(TENANT, ACTOR, "plan.read", APP, ENV),
        REVISION,
        [{"site_id": SITE, "endpoint_id": ENDPOINT, "generation_id": GENERATION}],
        {SITE: "a" * 64},
        "application.provision",
        "native_api",
    )
    assert result == catalogue
    assert rows == [
        {
            "destination": destination,
            "profile": profile,
            "policy": policy,
            "qualification": qualification,
        }
    ]


@pytest.mark.parametrize(
    "fault",
    [
        "group_writable",
        "world_writable",
        "symlink",
        "parent_symlink",
        "fifo",
        "oversize",
        "boolean_version",
    ],
)
def test_untrusted_policy_file_rejected_before_owner_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    directory = tmp_path / "configuration"
    directory.mkdir()
    path = directory / "registry.json"
    path.write_text(json.dumps({"schema_version": True if fault == "boolean_version" else 1}))
    if fault in {"group_writable", "world_writable"}:
        path.chmod(0o664 if fault == "group_writable" else 0o646)
    elif fault == "symlink":
        link = tmp_path / "registry-link.json"
        link.symlink_to(path)
        path = link
    elif fault == "parent_symlink":
        link = tmp_path / "configuration-link"
        link.symlink_to(directory, target_is_directory=True)
        path = link / path.name
    elif fault == "fifo":
        path.unlink()
        os.mkfifo(path)
    elif fault == "oversize":
        path.write_bytes(b" " * 524289)
    monkeypatch.setenv("PLANNING_REGISTRY_FILE", str(path))
    owner_read = Mock()
    monkeypatch.setattr("planning.infrastructure.owners.request", owner_read)
    with pytest.raises(Rejected, match="invalid_owner_input") as error:
        OwnerSources().resolve(
            Actor(TENANT, ACTOR, "plan.read", APP, ENV),
            REVISION,
            [{"site_id": SITE, "endpoint_id": ENDPOINT, "generation_id": GENERATION}],
            {SITE: "a" * 64},
            "application.provision",
            "native_api",
        )
    assert error.value.status == 503
    owner_read.assert_not_called()
