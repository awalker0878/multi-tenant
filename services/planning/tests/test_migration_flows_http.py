"""Application-flow selectors are scoped delegated reads and revisioned writes."""
import json
from unittest.mock import Mock

from planning_fixture import ACTOR, APP, ENV, SITE, TENANT
from test_planning_http import exchange
from planning.domain.model import Actor
from planning.interfaces.migration import MigrationPreparationApp

HEADERS = [
    (b"authorization", b"Bearer " + b"a" * 64),
    (b"x-actor-delegation", b"b" * 64),
    (b"content-type", b"application/json"),
    (b"idempotency-key", b"00000000-0000-4000-8000-000000000001"),
]


def test_app_flow_choices_require_current_site_authorization():
    authority, flows = Mock(), Mock()
    authority.actor.return_value = Actor(TENANT, ACTOR, "plan.read", APP, ENV)
    flows.read.return_value = {
        "context_sha256": "a" * 64, "revision": 0,
        "expires_at": 1234, "choices": [], "selections": [],
        "holds": ["application_flow_required_selection_missing"],
        "status": "held", "native_write_authorized": False,
    }
    app = MigrationPreparationApp(authority, Mock(), flows=flows)
    status, result = exchange(
        app, "/migration-flow-choices", json.dumps({"site_id": SITE}).encode(), HEADERS)
    assert status == 200 and result["native_write_authorized"] is False
    assert authority.actor.call_args.args[2:6] == (
        TENANT, "plan.read", APP, ENV)
    flows.read.assert_called_once_with(authority.actor.return_value, SITE, "b" * 64)
    bad = json.dumps({"site_id": SITE, "unobserved_native_rule": "manual"}).encode()
    assert exchange(app, "/migration-flow-choices", bad, HEADERS)[0] == 422


def test_app_flow_save_has_idempotency_key_and_does_not_accept_untrusted_evidence():
    authority, flows = Mock(), Mock()
    authority.actor.return_value = Actor(TENANT, ACTOR, "plan.create", APP, ENV)
    flows.save.return_value = {
        "revision": 1, "status": "held",
        "holds": ["required_native_flow_unknown"],
        "native_write_authorized": False,
    }
    app = MigrationPreparationApp(authority, Mock(), flows=flows)
    body = {
        "site_id": SITE, "revision": 0, "context_sha256": "a" * 64,
        "omissions": [], "selections": [{
            "source_flow_id": "b" * 64,
            "rule_native_ref": "existing-native-rule",
            "route_native_ref": "existing-native-route",
        }],
    }
    status, result = exchange(
        app, "/migration-flow-selections", json.dumps(body).encode(), HEADERS)
    assert status == 200 and result["status"] == "held"
    assert authority.actor.call_args.args[2:6] == (
        TENANT, "plan.create", APP, ENV)
    flows.save.assert_called_once_with(
        authority.actor.return_value, SITE, "b" * 64,
        body, "00000000-0000-4000-8000-000000000001")
    body["firewall"] = {"definition": "allow all"}
    assert exchange(
        app, "/migration-flow-selections", json.dumps(body).encode(), HEADERS)[0] == 422
