"""Authenticated API exercises real journals; no caller-provided authority or budgets."""

from typing import Any
from unittest.mock import MagicMock

from test_campaign_http import request
from test_expansion import AdoptionOwner, EnterpriseOwner, scope, spec, uid

from lifecycle.application.adoption import Adoptions
from lifecycle.application.enterprise import Enterprise
from lifecycle.domain.execution import Rejected
from lifecycle.interfaces.expansion import ExpansionApp


def test_adoption_api_scopes_every_action_and_denies_forged_owner_proof(database: Any) -> None:
    owner = AdoptionOwner()
    adoptions = Adoptions(database, owner, lambda: 100)
    enterprise = Enterprise(database, EnterpriseOwner(), lambda: 100)
    authority = MagicMock()
    authority.actor.return_value = uid()
    app = ExpansionApp(adoptions, enterprise, authority, MagicMock())
    tenant, native = uid(), scope()
    path = f"/v1/tenants/{tenant}/expansion/adoptions"
    status, result = request(app, path, {"scope": native, "fields": ["cpu.count"]})
    assert status == 201 and result["state"] == "observed"
    assert authority.actor.call_args.args[3] == {
        k: native[k] for k in ("site_id", "environment", "resource_id")
    }
    record = path + "/" + result["id"]
    assert request(app, record)[0] == 200
    assert (
        request(
            app,
            record + "/commands",
            {
                "action": "import",
                "expected_revision": 1,
                "proposed_fields": owner.values,
                "grant_write": True,
            },
        )[0]
        == 422
    )
    assert (
        request(
            app,
            record + "/commands",
            {"action": "import", "expected_revision": 1, "proposed_fields": owner.values},
        )[1]["state"]
        == "imported"
    )
    authority.actor.side_effect = Rejected("scope_denied", 403)
    assert request(app, record)[0] == 403
    assert (
        request(
            app,
            record + "/commands",
            {"action": "transfer", "expected_revision": 2, "proposed_fields": None},
        )[0]
        == 403
    )
    assert adoptions.read(tenant, result["id"])["state"] == "imported"


def test_wave_api_uses_owned_plans_and_cannot_claim_or_release_budget(database: Any) -> None:
    owner = EnterpriseOwner()
    enterprise = Enterprise(database, owner, lambda: 100)
    authority = MagicMock()
    authority.actor.return_value = uid()
    planned = spec()
    plans = MagicMock(return_value=planned)
    app = ExpansionApp(
        Adoptions(database, AdoptionOwner(), lambda: 100), enterprise, authority, plans
    )
    path = f"/v1/tenants/{planned['tenant_id']}/expansion/waves"
    reference = {"id": uid(), "revision": 1, "sha256": "f" * 64}
    status, wave = request(app, path, {"plans": [reference]})
    assert status == 201
    plans.assert_called_once_with(planned["tenant_id"], reference)
    assert request(app, path + "/" + wave["id"] + "/claim", {})[0] == 404
    assert (
        request(
            app,
            path + "/" + wave["id"] + "/commands",
            {"action": "resume", "expected_revision": 1, "release_allocations": True},
        )[0]
        == 422
    )
    assert request(app, path, {"plans": [reference], "budgets": {}})[0] == 422
