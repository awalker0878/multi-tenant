"""Production support reads and admission never inherit another direction's evidence."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from planning_fixture import SITE
from test_expansion import baseline
from test_planning_http import exchange

from planning.application.migration_support import MigrationSupport
from planning.domain.expansion import matrix
from planning.domain.model import Actor, Rejected, digest
from planning.infrastructure.migration_support import selected_tranche
from planning.interfaces.migration import MigrationPreparationApp


def test_current_direction_binding_and_revocation_are_rechecked() -> None:
    selected = baseline()
    for index, row in enumerate(selected["routes"]):
        row["source"]["profile_sha256"] = digest([index, "source"])
        row["target"]["profile_sha256"] = digest([index, "target"])
    route = selected["routes"][0]
    proof: dict[str, Any] = {
        "route_sha256": digest(route),
        "tranche_sha256": digest(selected),
        "release_sha256": selected["release_sha256"],
        "level": "E3",
        "decision": "accepted",
        "revoked": False,
        "expires_at": 180,
        "evidence_sha256": "a" * 64,
    }
    actor = Actor(str(uuid4()), str(uuid4()), "plan.read", str(uuid4()), str(uuid4()))
    support = MigrationSupport(lambda *_: selected, lambda *_: [proof], lambda: 100)
    binding = {
        "source": {"profile_sha256": route["source"]["profile_sha256"]},
        "target": {"profile_sha256": route["target"]["profile_sha256"]},
        "method": "VM_COLD_EXPORT",
    }
    assert len(support.read(actor, str(uuid4()))["directions"]) == 9
    support.require(actor, str(uuid4()), binding)
    reverse = deepcopy(binding)
    reverse["source"], reverse["target"] = reverse["target"], reverse["source"]
    with pytest.raises(Rejected, match="not_selected"):
        support.require(actor, str(uuid4()), reverse)
    proof["revoked"] = True
    with pytest.raises(Rejected, match="qualification_required"):
        support.require(actor, str(uuid4()), binding)


def test_no_qualification_inheritance_from_component_tests() -> None:
    selected = baseline()
    actor = Actor(str(uuid4()), str(uuid4()), "plan.read", str(uuid4()), str(uuid4()))
    support = MigrationSupport(lambda *_: selected, lambda *_: [], lambda: 100)
    response = support.read(actor, str(uuid4()))
    assert response["native_write_authorized"] is False
    assert all(
        not route["native_qualified"] for row in response["directions"] for route in row["routes"]
    )


def test_operating_acceptance_requires_both_independent_levels() -> None:
    selected = baseline()
    proof = {
        "route_sha256": digest(selected["routes"][0]),
        "tranche_sha256": digest(selected),
        "release_sha256": selected["release_sha256"],
        "level": "E3",
        "decision": "accepted",
        "revoked": False,
        "expires_at": 180,
        "evidence_sha256": "c" * 64,
    }
    accepted = proof | {"level": "E4", "evidence_sha256": "d" * 64}
    assert not matrix(selected, [accepted], 100)[0]["routes"][0]["native_qualified"]
    assert matrix(selected, [proof, accepted], 100)[0]["routes"][0]["operationally_accepted"]
    assert not matrix(selected, [proof, accepted | {"revoked": True}], 100)[0]["routes"][0][
        "operationally_accepted"
    ]
    assert not matrix(selected, [proof, accepted, accepted], 100)[0]["routes"][0][
        "operationally_accepted"
    ]


def test_protected_registry_cannot_cross_scope_or_be_writable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    actor = Actor(str(uuid4()), str(uuid4()), "plan.read", str(uuid4()), str(uuid4()))
    path = tmp_path / "routes.json"
    selection = baseline()
    scope = {
        "tenant_id": actor.tenant,
        "site_id": SITE,
        "resource_id": actor.application,
        "environment": actor.environment,
    }
    path.write_text(
        json.dumps({"schema_version": 1, "assignments": [{"scope": scope, "tranche": selection}]})
    )
    path.chmod(0o600)
    monkeypatch.setenv("PLANNING_MIGRATION_SUPPORT_FILE", str(path))
    assert selected_tranche(actor, SITE) == selection
    with pytest.raises(Rejected, match="unassigned"):
        selected_tranche(actor, str(uuid4()))
    path.chmod(0o666)
    with pytest.raises(Rejected, match="unavailable"):
        selected_tranche(actor, SITE)
    path.chmod(0o600)
    link = tmp_path / "link"
    link.symlink_to(path)
    monkeypatch.setenv("PLANNING_MIGRATION_SUPPORT_FILE", str(link))
    with pytest.raises(Rejected, match="unavailable"):
        selected_tranche(actor, SITE)


def test_support_http_uses_read_delegation_and_cannot_accept_browser_evidence() -> None:
    authority, support = Mock(), Mock()
    support.read.return_value = {"directions": [], "native_write_authorized": False}
    app: Any = MigrationPreparationApp(authority, Mock(), support=support)
    headers = [
        (b"authorization", b"Bearer " + b"a" * 64),
        (b"content-type", b"application/json"),
        (b"x-actor-delegation", b"b" * 64),
    ]
    assert (
        exchange(app, "/migration-support", json.dumps({"site_id": SITE}).encode(), headers)[0]
        == 200
    )
    assert authority.actor.call_args.args[3] == "plan.read"
    support.reset_mock()
    assert (
        exchange(
            app,
            "/migration-support",
            json.dumps({"site_id": SITE, "records": []}).encode(),
            headers,
        )[0]
        == 422
    )
    support.read.assert_not_called()
    authority.actor.side_effect = Rejected("denied", 403)
    assert (
        exchange(app, "/migration-support", json.dumps({"site_id": SITE}).encode(), headers)[0]
        == 403
    )
    support.read.assert_not_called()
