"""Executable owner-operation response contract tests (no live network)."""
from __future__ import annotations

import json

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from planning.domain.model import Rejected
from planning.infrastructure import owners
from planning.infrastructure.owner_contracts import (
    OWNER_OPERATIONS, contract_for_operation,
)


TENANT = "10000000-0000-4000-8000-000000000001"
APP = "10000000-0000-4000-8000-000000000002"
ENV = "10000000-0000-4000-8000-000000000003"
SITE = "10000000-0000-4000-8000-000000000004"
SHA = "a" * 64


@pytest.mark.parametrize(("owner", "method", "path", "expected"), [
    ("INVENTORY", "GET", f"/internal/tenants/{TENANT}/migration-inputs/{APP}/{ENV}/{SITE}/1/{SHA}", "migration-input-v4"),
    ("INVENTORY", "GET", f"/v1/tenants/{TENANT}/migration-inputs/{APP}/{ENV}/{SITE}/1/{SHA}", "migration-input-v4"),
    ("INVENTORY", "GET", f"/v1/tenants/{TENANT}/planning-capability-inputs/{APP}/{ENV}/{SITE}/{APP}/{ENV}", "inventory-input-v2"),
    ("CATALOGUE", "GET", f"/v1/tenants/{TENANT}/planning-inputs/{APP}/{ENV}/{SITE}/{APP}", "catalogue-input-v1"),
    ("CATALOGUE", "GET", f"/internal/tenants/{TENANT}/applications/{APP}/environments/{ENV}/current-planning-intent", "catalogue-current-v2"),
    ("ASSURANCE", "POST", f"/v1/tenants/{TENANT}/migration-qualifications", "migration-support-v2"),
    ("ASSURANCE", "POST", f"/v1/tenants/{TENANT}/planning-qualification-v2", "qualification-v2.1"),
    ("ASSURANCE", "POST", f"/internal/tenants/{TENANT}/qualification-checks", "qualification-v2.1"),
])
def test_runtime_operation_has_one_immutable_schema(owner, method, path, expected):
    assert contract_for_operation(owner, method, path) == expected
    assert contract_for_operation(owner, method, path, expected) == expected
    with pytest.raises(ValueError, match="owner_contract_operation_unavailable"):
        contract_for_operation(owner, method, path, "migration-input-v3")
    with pytest.raises(ValueError, match="owner_contract_operation_unavailable"):
        contract_for_operation(owner, "DELETE", path, expected)


def test_undocumented_owner_route_fails_closed():
    with pytest.raises(ValueError):
        contract_for_operation("ASSURANCE", "POST", f"/internal/tenants/{TENANT}/unregistered")
    assert len(OWNER_OPERATIONS) == 7


def test_real_owner_transport_validates_qualified_assurance_response(monkeypatch):
    payload = {
        "schema_version": 1,
        "scope": {"tenant_id": TENANT, "site_id": SITE,
                  "resource_id": APP, "environment": ENV},
        "tranche_sha256": SHA,
        "release_sha256": SHA,
        "records": [],
        "native_write_authorized": False,
        "api_evidence": {},
        "flow_evidence": None,
    }
    body = [payload]

    class Response:
        status = 200
        def read(self, max_bytes):
            return json.dumps(body[0]).encode()
        def getheader(self, name, default=None):
            return "identity"

    class Connection:
        def __init__(self, *args, **kwargs):
            pass
        def request(self, method, path, data, headers):
            assert method == "POST"
            assert path.endswith("/migration-qualifications")
        def getresponse(self):
            return Response()
        def close(self):
            pass

    monkeypatch.setenv("ASSURANCE_URL", "https://assurance.example")
    monkeypatch.setenv("ASSURANCE_CA_FILE", "/tmp/ca.pem")
    monkeypatch.setattr(owners, "mounted_secret", lambda _: "test-only-token")
    monkeypatch.setattr(owners.ssl, "create_default_context", lambda **kwargs: object())
    monkeypatch.setattr(owners.http.client, "HTTPSConnection", Connection)
    path = f"/v1/tenants/{TENANT}/migration-qualifications"
    assert owners.request("ASSURANCE", "POST", path, {}, schema_name="migration-support-v2") == payload
    for invalid in (
        {**payload, "api_evidence": []},
        {**payload, "flow_evidence": {"decision": "accepted"}},
        {**payload, "unapproved_extra": True},
    ):
        body[0] = invalid
        with pytest.raises(Rejected) as error:
            owners.request("ASSURANCE", "POST", path, {}, schema_name="migration-support-v2")
        assert error.value.status == 503
    with pytest.raises(Rejected) as error:
        owners.request("ASSURANCE", "POST", path, {}, schema_name="migration-support-v1")
    assert error.value.status == 503


def test_catalogue_current_v2_validates_nested_intent_not_only_envelope():
    from importlib.resources import files

    base = files("planning.infrastructure.inputs")
    original = json.loads(base.joinpath("catalogue-input-v1.json").read_text())
    current = json.loads(base.joinpath("catalogue-current-v2.json").read_text())
    assert current["$defs"]["Intent"] == original["components"]["schemas"]["Intent"]
    validator = Draft202012Validator(current, format_checker=FormatChecker())
    shallow = {"revision_id": TENANT, "intent_sha256": SHA,
               "intent": {"workloads": "bad", "datasets": "bad",
                          "dependencies": "bad", "environment": {"id": ENV}}}
    assert list(validator.iter_errors(shallow))


def test_catalogue_current_owner_response_uses_real_published_intent(monkeypatch):
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    source = json.loads((root / "contracts/fixtures/catalogue/permit-desk-v1.json").read_text())
    payload = {"revision_id": TENANT, "intent_sha256": SHA, "intent": source}
    wire = [payload]

    class Response:
        status = 200
        def read(self, n):
            return json.dumps(wire[0]).encode()
        def getheader(self, name, default=None):
            return "identity"

    class Connection:
        def __init__(self, *args, **kwargs):
            pass
        def request(self, method, path, data, headers):
            assert method == "GET" and path.endswith("/current-planning-intent")
        def getresponse(self):
            return Response()
        def close(self):
            pass

    monkeypatch.setenv("CATALOGUE_URL", "https://catalogue.example")
    monkeypatch.setenv("CATALOGUE_CA_FILE", "/tmp/ca.pem")
    monkeypatch.setattr(owners, "mounted_secret", lambda _: "test-only-token")
    monkeypatch.setattr(owners.ssl, "create_default_context", lambda **kwargs: object())
    monkeypatch.setattr(owners.http.client, "HTTPSConnection", Connection)
    path = (f"/internal/tenants/{TENANT}/applications/{APP}"
            f"/environments/{ENV}/current-planning-intent")
    assert owners.request("CATALOGUE", "GET", path, schema_name="catalogue-current-v2") == payload
    wire[0] = {**payload, "intent": {**source, "workloads": "not-a-list"}}
    with pytest.raises(Rejected) as invalid:
        owners.request("CATALOGUE", "GET", path, schema_name="catalogue-current-v2")
    assert invalid.value.status == 503
    with pytest.raises(Rejected):
        owners.request("CATALOGUE", "GET", path, schema_name="catalogue-current-v1")
