"""Executable owner-operation response contract tests (no live network)."""

from __future__ import annotations

import http.client
import json
import ssl
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from planning.domain.model import Rejected
from planning.infrastructure import owners
from planning.infrastructure.owner_contracts import (
    OWNER_OPERATIONS,
    contract_for_operation,
)

TENANT = "10000000-0000-4000-8000-000000000001"
APP = "10000000-0000-4000-8000-000000000002"
ENV = "10000000-0000-4000-8000-000000000003"
SITE = "10000000-0000-4000-8000-000000000004"
SHA = "a" * 64


@pytest.mark.parametrize(
    ("owner", "method", "path", "expected"),
    [
        (
            "INVENTORY",
            "GET",
            f"/internal/tenants/{TENANT}/migration-inputs/{APP}/{ENV}/{SITE}/1/{SHA}",
            "migration-input-v4",
        ),
        (
            "INVENTORY",
            "GET",
            f"/v1/tenants/{TENANT}/migration-inputs/{APP}/{ENV}/{SITE}/1/{SHA}",
            "migration-input-v4",
        ),
        (
            "INVENTORY",
            "GET",
            f"/v1/tenants/{TENANT}/planning-capability-inputs/{APP}/{ENV}/{SITE}/{APP}/{ENV}",
            "inventory-input-v2",
        ),
        (
            "CATALOGUE",
            "GET",
            f"/v1/tenants/{TENANT}/planning-inputs/{APP}/{ENV}/{SITE}/{APP}",
            "catalogue-input-v1",
        ),
        (
            "CATALOGUE",
            "GET",
            f"/internal/tenants/{TENANT}/applications/{APP}/environments/{ENV}/current-planning-intent",
            "catalogue-current-v2",
        ),
        (
            "ASSURANCE",
            "POST",
            f"/v1/tenants/{TENANT}/migration-qualifications",
            "migration-support-v2",
        ),
        (
            "ASSURANCE",
            "POST",
            f"/v1/tenants/{TENANT}/planning-qualification-v2",
            "qualification-v3",
        ),
        (
            "ASSURANCE",
            "POST",
            f"/internal/tenants/{TENANT}/qualification-checks",
            "qualification-v3",
        ),
        (
            "GOVERNANCE",
            "POST",
            f"/v1/tenants/{TENANT}/delegated-authorizations",
            "governance-delegation-response-v2",
        ),
        (
            "LIFECYCLE",
            "POST",
            f"/internal/tenants/{TENANT}/placement-reservations/checks",
            "placement-reservation-v1",
        ),
    ],
)
def test_runtime_operation_has_one_immutable_schema(
    owner: Any, method: Any, path: Any, expected: Any
) -> None:
    assert contract_for_operation(owner, method, path) == expected
    assert contract_for_operation(owner, method, path, expected) == expected
    with pytest.raises(ValueError, match="owner_contract_operation_unavailable"):
        contract_for_operation(owner, method, path, "unsupported-input-v99")
    with pytest.raises(ValueError, match="owner_contract_operation_unavailable"):
        contract_for_operation(owner, "DELETE", path, expected)


def test_undocumented_owner_route_fails_closed() -> None:
    with pytest.raises(ValueError):
        contract_for_operation("ASSURANCE", "POST", f"/internal/tenants/{TENANT}/unregistered")
    assert len(OWNER_OPERATIONS) == 9


def test_real_owner_transport_validates_qualified_assurance_response(monkeypatch: Any) -> None:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "scope": {"tenant_id": TENANT, "site_id": SITE, "resource_id": APP, "environment": ENV},
        "tranche_sha256": SHA,
        "release_sha256": SHA,
        "records": [],
        "native_write_authorized": False,
        "api_evidence": {},
        "flow_evidence": None,
    }
    body: list[Any] = [payload]
    response_status = [200]

    class Response:
        @property
        def status(self) -> int:
            return response_status[0]

        def read(self: Any, max_bytes: Any) -> Any:
            return json.dumps(body[0]).encode()

        def getheader(self: Any, name: Any, default: Any = None) -> Any:
            return "identity"

    class Connection:
        def __init__(self: Any, *args: Any, **kwargs: Any) -> None:
            pass

        def request(self: Any, method: Any, path: Any, data: Any, headers: Any) -> None:
            assert method == "POST"
            assert path.endswith("/migration-qualifications")

        def getresponse(self: Any) -> Any:
            return Response()

        def close(self: Any) -> None:
            pass

    monkeypatch.setenv("ASSURANCE_URL", "https://assurance.example")
    monkeypatch.setenv("ASSURANCE_CA_FILE", "/tmp/ca.pem")
    monkeypatch.setattr(owners, "mounted_secret", lambda _: "test-only-token")
    monkeypatch.setattr(ssl, "create_default_context", lambda **kwargs: object())
    monkeypatch.setattr(http.client, "HTTPSConnection", Connection)
    path = f"/v1/tenants/{TENANT}/migration-qualifications"
    assert (
        owners.request("ASSURANCE", "POST", path, {}, schema_name="migration-support-v2") == payload
    )
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
        owners.request("ASSURANCE", "POST", path, {}, schema_name="unsupported-response-v99")
    assert error.value.status == 503

    response_status[0] = 403
    body[0] = {
        "code": "qualification_request_denied",
        "message": "Denied",
        "correlation_id": TENANT,
        "retryable": False,
    }
    with pytest.raises(Rejected) as denied:
        owners.request("ASSURANCE", "POST", path, {})
    assert denied.value.status == 403
    body[0] = {"error": "denied", "uncontracted": True}
    with pytest.raises(Rejected) as incompatible:
        owners.request("ASSURANCE", "POST", path, {})
    assert incompatible.value.status == 503


def test_catalogue_current_v2_validates_nested_intent_not_only_envelope() -> None:
    from importlib.resources import files

    base = files("planning.infrastructure.inputs")
    original = json.loads(base.joinpath("catalogue-input-v1.json").read_text())
    current = json.loads(base.joinpath("catalogue-current-v2.json").read_text())
    assert current["$defs"]["Intent"] == original["components"]["schemas"]["Intent"]
    validator = Draft202012Validator(current, format_checker=FormatChecker())
    shallow: dict[str, Any] = {
        "revision_id": TENANT,
        "intent_sha256": SHA,
        "intent": {
            "workloads": "bad",
            "datasets": "bad",
            "dependencies": "bad",
            "environment": {"id": ENV},
        },
    }
    assert list(validator.iter_errors(shallow))


def test_catalogue_current_owner_response_uses_real_published_intent(monkeypatch: Any) -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    source = json.loads((root / "contracts/fixtures/catalogue/permit-desk-v1.json").read_text())
    payload: dict[str, Any] = {"revision_id": TENANT, "intent_sha256": SHA, "intent": source}
    wire: list[Any] = [payload]

    class Response:
        status = 200

        def read(self: Any, n: Any) -> Any:
            return json.dumps(wire[0]).encode()

        def getheader(self: Any, name: Any, default: Any = None) -> Any:
            return "identity"

    class Connection:
        def __init__(self: Any, *args: Any, **kwargs: Any) -> None:
            pass

        def request(self: Any, method: Any, path: Any, data: Any, headers: Any) -> None:
            assert method == "GET" and path.endswith("/current-planning-intent")

        def getresponse(self: Any) -> Any:
            return Response()

        def close(self: Any) -> None:
            pass

    monkeypatch.setenv("CATALOGUE_URL", "https://catalogue.example")
    monkeypatch.setenv("CATALOGUE_CA_FILE", "/tmp/ca.pem")
    monkeypatch.setattr(owners, "mounted_secret", lambda _: "test-only-token")
    monkeypatch.setattr(ssl, "create_default_context", lambda **kwargs: object())
    monkeypatch.setattr(http.client, "HTTPSConnection", Connection)
    path = (
        f"/internal/tenants/{TENANT}/applications/{APP}/environments/{ENV}/current-planning-intent"
    )
    assert owners.request("CATALOGUE", "GET", path, schema_name="catalogue-current-v2") == payload
    wire[0] = {**payload, "intent": {**source, "workloads": "not-a-list"}}
    with pytest.raises(Rejected) as invalid:
        owners.request("CATALOGUE", "GET", path, schema_name="catalogue-current-v2")
    assert invalid.value.status == 503
    with pytest.raises(Rejected):
        owners.request("CATALOGUE", "GET", path, schema_name="catalogue-current-v1")


def test_capacity_and_governance_owner_responses_are_schema_and_scope_validated(
    monkeypatch: Any,
) -> None:
    from copy import deepcopy

    scope: dict[str, Any] = {"site_id": SITE, "environment": ENV, "resource_id": APP}
    delegation: dict[str, Any] = {
        "allowed": True,
        "delegation_id": TENANT,
        "actor_id": APP,
        "delegating_service": "console",
        "audience": "planning",
        "tenant_id": TENANT,
        "action": "plan.read",
        "scope": scope,
        "expires_at": "2026-10-12T15:00:00Z",
        "evaluated_at": "2026-10-12T14:59:00Z",
        "authority_use": "request_bound",
    }
    reservation: dict[str, Any] = {
        "schema_version": 1,
        "reservation_id": APP,
        "tenant_id": TENANT,
        "plan_digest": SHA,
        "request_digest": SHA,
        "placement_sha256": SHA,
        "generation_id": ENV,
        "policy_sha256": SHA,
        "allocations": [
            {
                "workload_id": APP,
                "pool_id": SHA,
                "native_ref": "provider-host",
                "vector": {"vcpus": 2, "memory_mib": 4096, "storage_gib": 20, "addresses": 1},
            }
        ],
        "state": "reserved",
        "observed_at": 2000000000,
        "expires_at": 2000000030,
        "revision": 1,
        "native_write_authorized": False,
    }
    wire: list[Any] = [delegation]

    class Response:
        status = 200

        def read(self: Any, n: Any) -> Any:
            return json.dumps(wire[0]).encode()

        def getheader(self: Any, name: Any, default: Any = None) -> Any:
            return "identity"

    class Connection:
        def __init__(self: Any, *args: Any, **kwargs: Any) -> None:
            pass

        def request(self: Any, method: Any, path: Any, data: Any, headers: Any) -> None:
            assert method == "POST" and path.startswith(("/v1/tenants/", "/internal/tenants/"))

        def getresponse(self: Any) -> Any:
            return Response()

        def close(self: Any) -> None:
            pass

    for owner in ("GOVERNANCE", "LIFECYCLE"):
        monkeypatch.setenv(owner + "_URL", "https://owner.example")
        monkeypatch.setenv(owner + "_CA_FILE", "/tmp/ca.pem")
    monkeypatch.setattr(owners, "mounted_secret", lambda _: "test-only-token")
    monkeypatch.setattr(ssl, "create_default_context", lambda **kwargs: object())
    monkeypatch.setattr(http.client, "HTTPSConnection", Connection)

    routes: list[Any] = [
        (
            "GOVERNANCE",
            f"/v1/tenants/{TENANT}/delegated-authorizations",
            {"action": "plan.read", "scope": scope},
            delegation,
        ),
        (
            "LIFECYCLE",
            f"/internal/tenants/{TENANT}/placement-reservations/checks",
            {"plan_digest": SHA},
            reservation,
        ),
    ]
    for owner, path, body, success in routes:
        wire[0] = success
        assert owners.request(owner, "POST", path, body) == success
        violations: list[Any] = [
            {**success, "tenant_id": SITE},
            {**success, "unexpected": True},
        ]
        if owner == "GOVERNANCE":
            violations.extend(
                [
                    {**success, "scope": {**scope, "site_id": TENANT}},
                    {**success, "audience": "inventory"},
                ]
            )
        else:
            violations.extend(
                [
                    {**success, "native_write_authorized": True},
                    {**success, "plan_digest": "f" * 64},
                    {
                        **success,
                        "allocations": [{**success["allocations"][0], "vector": {"vcpus": "2"}}],
                    },
                ]
            )
        for invalid in violations:
            wire[0] = deepcopy(invalid)
            with pytest.raises(Rejected) as error:
                owners.request(owner, "POST", path, body)
            assert error.value.status == 503
