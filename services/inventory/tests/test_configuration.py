"API-first configuration review against the real Inventory runtime database role."

import copy
from dataclasses import replace
from typing import Any

import psycopg
import pytest
from test_discovery import Campaign, row

from inventory.application.configuration import PortingConfiguration
from inventory.application.discovery import uid
from inventory.domain.configuration import CAPABILITIES, configuration_fact, manual_input
from inventory.domain.discovery import Rejected
from inventory.infrastructure.generated_configuration_streams import configuration_streams

pytest_plugins = ["test_discovery"]


def draft(endpoint: str | None = None) -> dict[str, Any]:
    return {
        "source_endpoint": endpoint,
        "target_endpoint": endpoint,
        "manual": {},
        "choices": [
            {"id": c["id"], "required": False, "interpretation": "observed", "reason": ""}
            for c in CAPABILITIES
        ],
    }


def pull(c: Campaign) -> str:
    c.service.configuration_streams = configuration_streams
    job = c.service.command(c.actor, "configuration_pull", {}, uid(), c.endpoint)["discovery_id"]
    streams = configuration_streams(c.policy.streams, c.policy.platform)
    for i, stream in enumerate(streams):
        c.now += 2
        lease = c.service.claim(c.worker)["job"]
        assert lease["collect_configuration"] is True and lease["stream"] == i
        body = c.page(lease, [])
        if stream["kind"].startswith("config_"):
            query = stream["kind"][7:]
            body["configuration"] = {
                "query": query,
                "status": "observed",
                "items": [
                    {
                        "id": "port-security" if query == "network_extensions" else "fixture",
                        "name": "Fixture",
                        "attributes": [],
                    }
                ],
            }
        result = c.service.submit(c.worker, body)
    assert result["status"] == "complete"
    return str(job)


def test_draft_needs_no_native_connection_and_is_idempotent(campaign: Campaign) -> None:
    c = campaign
    app = PortingConfiguration(c.service)
    c.policies.values = {}  # Console onboarding must not depend on native policy readiness.
    key = uid()
    result = app.command(c.actor, "configuration_save", draft(), key)
    assert app.command(c.actor, "configuration_save", draft(), key) == result
    assert result["native_write_authorized"] is False
    assert app.read(c.actor)["holds"] == ["fresh_source_and_target_configuration_required"]
    with pytest.raises(Rejected, match="configuration_refresh_required"):
        app.command(
            c.actor, "configuration_confirm", {"digest": result["digest"]}, uid(), expected=1
        )
    with pytest.raises(Rejected, match="idempotency_conflict"):
        app.command(
            c.actor,
            "configuration_save",
            {**draft(), "manual": {"ownership_reference": "ref"}},
            key,
        )


def test_pull_confirm_edit_and_refresh_keep_immutable_provenance(campaign: Campaign) -> None:
    c = campaign
    generation = pull(c)
    app = PortingConfiguration(c.service)
    body = draft(c.endpoint)
    body["choices"][0].update(
        required=True, interpretation="exclude", reason="Not used by workload; review R1"
    )
    saved = app.command(c.actor, "configuration_save", body, uid())
    before = app.read(c.actor)
    assert before["source"]["generation_id"] == generation
    assert before["capabilities"][0]["source_state"] == "configured"
    assert before["configuration"]["choices"][0]["interpretation"] == "exclude"
    assert before["native_write_authorized"] is False
    app.command(c.actor, "configuration_confirm", {"digest": saved["digest"]}, uid(), expected=1)
    assert app.read(c.actor)["configuration"]["confirmation_current"] is True
    # New API generation invalidates the confirmation even if the values happen to match.
    pull(c)
    assert app.read(c.actor)["holds"] == ["api_configuration_changed"]
    with pytest.raises(Rejected, match="configuration_refresh_required"):
        app.command(
            c.actor, "configuration_confirm", {"digest": saved["digest"]}, uid(), expected=1
        )
    app.command(c.actor, "configuration_save", body, uid(), expected=1)
    assert app.read(c.actor)["configuration"]["confirmed_at"] is None
    with c.database.transaction() as tx:
        assert row(tx, "SELECT count(*) AS n FROM inventory.porting_revisions")["n"] == 2
        assert row(tx, "SELECT count(*) AS n FROM inventory.porting_confirmations")["n"] == 1
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with c.database.transaction() as tx:
            tx.execute("DELETE FROM inventory.porting_revisions")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with c.database.transaction() as tx:
            tx.execute("UPDATE inventory.configuration_facts SET payload='{}'")


def test_expiry_revocation_scoping_and_preconditions(campaign: Campaign) -> None:
    c = campaign
    pull(c)
    app = PortingConfiguration(c.service)
    result = app.command(c.actor, "configuration_save", draft(c.endpoint), uid())
    for wrong in (replace(c.actor, tenant=uid()), replace(c.actor, site=uid())):
        assert app.read(wrong)["configuration"] is None
        with pytest.raises(Rejected, match="not_found"):
            app.command(wrong, "configuration_save", draft(c.endpoint), uid())
    for expected, reason in ((None, "revision_required"), (2, "stale_revision")):
        with pytest.raises(Rejected, match=reason):
            app.command(c.actor, "configuration_save", draft(), uid(), expected=expected)
    with pytest.raises(Rejected, match="action_denied"):
        app.read(replace(c.actor, action="inventory.read"))
    c.now += 400
    assert "fresh_source_and_target_configuration_required" in app.read(c.actor)["holds"]
    with pytest.raises(Rejected, match="configuration_refresh_required"):
        app.command(
            c.actor, "configuration_confirm", {"digest": result["digest"]}, uid(), expected=1
        )
    c.held = True
    assert not app.read(c.actor)["source"]["current"]


@pytest.mark.parametrize(
    "field", ["api_version", "native_write_authorized", "capabilities", "credential", "bindings"]
)
def test_api_facts_and_authority_cannot_be_overridden(field: str) -> None:
    body = draft()
    body[field] = "forged"
    with pytest.raises(Rejected, match="unknown_field"):
        manual_input(body)
    body = draft()
    body["manual"][field] = "forged"
    with pytest.raises(Rejected, match="unknown_field"):
        manual_input(body)


def test_overrides_need_reasons_and_duplicate_choices_fail() -> None:
    body = draft()
    body["choices"][0]["interpretation"] = "include"
    with pytest.raises(Rejected, match="invalid_text"):
        manual_input(body)
    body["choices"][0]["reason"] = "Owner evidence R1; collector lacks backend semantics"
    manual_input(body)
    body["choices"][1] = copy.deepcopy(body["choices"][0])
    with pytest.raises(Rejected, match="invalid_capability_choices"):
        manual_input(body)


def test_configuration_fact_cannot_claim_observations_after_failed_read() -> None:
    with pytest.raises(Rejected, match="invalid_configuration_status"):
        configuration_fact(
            {
                "query": "network_extensions",
                "status": "permission_denied",
                "items": [{"id": "invented"}],
            },
            "network_extensions",
        )


def test_worker_cannot_attach_configuration_to_resource_stream(campaign: Campaign) -> None:
    c = campaign
    c.start()
    lease = c.service.claim(c.worker)["job"]
    body = c.page(lease, [])
    body["configuration"] = {"query": "network_extensions", "status": "observed", "items": []}
    with pytest.raises(Rejected, match="unexpected_configuration"):
        c.service.submit(c.worker, body)


def test_source_only_vmware_review_does_not_require_destination_permissions(
    campaign: Campaign,
) -> None:
    from test_workload_profiles import collected

    c = campaign
    collected(c, True)
    app = PortingConfiguration(c.service)
    body = draft(c.endpoint) | {"target_endpoint": None}
    saved = app.command(c.actor, "configuration_save", body, uid())
    view = app.read(c.actor)
    assert view["holds"] == []
    assert view["source"]["current"] is True
    assert view["source"]["queries"][0]["query"] == "vmware_source_workloads"
    assert view["source"]["queries"][0]["items"][0]["id"] == "vm-1"
    assert all(cap["source_state"] == "unknown" for cap in view["vmware_capabilities"])
    app.command(c.actor, "configuration_confirm", {"digest": saved["digest"]}, uid(), expected=1)
    assert app.read(c.actor)["configuration"]["confirmation_current"] is True
    c.now += 400
    assert not app.read(c.actor)["configuration"]["confirmation_current"]


def test_target_only_configuration_can_be_confirmed_for_provisioning(campaign: Campaign) -> None:
    c = campaign
    pull(c)
    app = PortingConfiguration(c.service)
    saved = app.command(
        c.actor, "configuration_save", draft(c.endpoint) | {"source_endpoint": None}, uid()
    )
    app.command(c.actor, "configuration_confirm", {"digest": saved["digest"]}, uid(), expected=1)
    assert app.read(c.actor)["configuration"]["confirmation_current"] is True
