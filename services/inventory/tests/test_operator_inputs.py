"""Operator collection integrity, tenant scope and unchanged native authority."""

from dataclasses import replace
from typing import Any

import psycopg
import pytest
from test_discovery import Campaign, row

from inventory.application.configuration import PortingConfiguration
from inventory.application.discovery import uid
from inventory.application.operator_inputs import OperatorInputs
from inventory.domain.configuration import CAPABILITIES
from inventory.domain.discovery import Rejected
from inventory.domain.operator_inputs import FIELDS, missing_fields, validate_values

pytest_plugins = ["test_discovery"]


def complete() -> dict[str, Any]:
    return {
        f["id"]: f["minimum"] if f["kind"] == "integer" else "record:" + f["id"] for f in FIELDS
    }


def test_zero_targets_are_supplied_and_every_field_is_described() -> None:
    values = complete()
    validate_values(values)
    assert missing_fields(values) == []
    assert values["max_outage_seconds"] == values["max_data_loss_bytes"] == 0
    assert len(FIELDS) == len({f["id"] for f in FIELDS}) == 32
    assert all(f["help"] and f["label"] and f["group"] for f in FIELDS)
    assert len(missing_fields({})) == 32


@pytest.mark.parametrize("value", [True, -1, 0.5, "0", None, 604801])
def test_invalid_targets_are_not_treated_as_approved(value: Any) -> None:
    with pytest.raises(Rejected, match="invalid_operator_target"):
        validate_values({"max_outage_seconds": value})


@pytest.mark.parametrize(
    "value",
    [
        "",
        "Bearer secret",
        "-----BEGIN PRIVATE KEY-----",
        "https://example.test/?token=secret",
        "a" * 241,
        [],
        {},
    ],
)
def test_references_are_bounded_identifiers(value: Any) -> None:
    with pytest.raises(Rejected, match="invalid_operator_reference"):
        validate_values({"trust_bundle_ref": value})


def test_shared_execution_and_verification_references_are_rejected() -> None:
    with pytest.raises(Rejected, match="independent_verification_account_required"):
        validate_values(
            {"target_writer_ref": "vault:shared", "source_observer_ref": "vault:shared"}
        )
    with pytest.raises(Rejected, match="unknown_field"):
        validate_values({"native_write_authorized": True})
    with pytest.raises(Rejected, match="unknown_field"):
        validate_values({"api_version": "invented"})


def test_draft_save_replay_and_immutable_history(campaign: Campaign) -> None:
    c = campaign
    app = OperatorInputs(c.service)
    key = uid()
    body = {"values": {"max_data_loss_bytes": 0}, "configuration_digest": None}
    result = app.command(c.actor, "operator_inputs_save", body, key)
    assert app.command(c.actor, "operator_inputs_save", body, key) == result
    view = app.read(c.actor)
    assert view["record"]["values"] == body["values"]
    assert "max_data_loss_bytes" not in view["missing_fields"]
    assert view["native_write_authorized"] is view["collection_complete"] is False
    assert view["tenant_id"] == c.actor.tenant and view["site_id"] == c.actor.site
    with pytest.raises(Rejected, match="idempotency_conflict"):
        app.command(c.actor, "operator_inputs_save", {**body, "values": {}}, key)
    app.command(c.actor, "operator_inputs_save", {**body, "values": {}}, uid(), expected=1)
    with c.database.transaction() as tx:
        assert row(tx, "SELECT count(*) AS n FROM inventory.operator_input_revisions")["n"] == 2
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with c.database.transaction() as tx:
            tx.execute("DELETE FROM inventory.operator_input_revisions")


def test_scope_access_and_stale_save(campaign: Campaign) -> None:
    c = campaign
    app = OperatorInputs(c.service)
    body: dict[str, Any] = {"values": {}, "configuration_digest": None}
    app.command(c.actor, "operator_inputs_save", body, uid())
    for actor in (replace(c.actor, tenant=uid()), replace(c.actor, site=uid())):
        assert app.read(actor)["record"] is None
    with pytest.raises(Rejected, match="action_denied"):
        app.read(replace(c.actor, action="inventory.read"))
    with pytest.raises(Rejected, match="action_denied"):
        app.command(replace(c.actor, action="inventory.read"), "operator_inputs_save", body, uid())
    for revision, reason in ((None, "revision_required"), (2, "stale_revision")):
        with pytest.raises(Rejected, match=reason):
            app.command(c.actor, "operator_inputs_save", body, uid(), expected=revision)


def test_complete_inputs_do_not_supply_environment_facts_or_native_qualification(
    campaign: Campaign,
) -> None:
    c = campaign
    app = OperatorInputs(c.service)
    body = {"values": complete(), "configuration_digest": None}
    app.command(c.actor, "operator_inputs_save", body, uid())
    view = app.read(c.actor)
    assert view["missing_fields"] == []
    assert view["holds"] == ["environment_review_required"]
    assert view["collection_complete"] is view["native_write_authorized"] is False
    configuration = PortingConfiguration(c.service)
    configuration.command(
        c.actor,
        "configuration_save",
        {
            "source_endpoint": None,
            "target_endpoint": None,
            "manual": {},
            "choices": [
                {"id": f["id"], "required": False, "interpretation": "observed", "reason": ""}
                for f in CAPABILITIES
            ],
        },
        uid(),
    )
    assert "environment_review_changed" in app.read(c.actor)["holds"]
    with pytest.raises(Rejected, match="environment_review_changed"):
        app.command(c.actor, "operator_inputs_save", body, uid(), expected=1)
    with pytest.raises(Rejected, match="unknown_field"):
        app.command(
            c.actor,
            "operator_inputs_save",
            {**body, "native_write_authorized": True},
            uid(),
            expected=1,
        )
