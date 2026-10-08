"""Bounded policy pagination preserves scope and never hides later enrollments."""

from contextlib import nullcontext
from dataclasses import replace
from unittest.mock import Mock

from test_discovery import PolicySet, policy_document

from inventory.application.discovery import Discovery, uid
from inventory.application.ports import Database, Transaction
from inventory.application.views import InventoryViews
from inventory.domain.discovery import Actor
from inventory.infrastructure.policies import parse_policy


def test_policy_pages_have_stable_cursors_and_preserve_tenant_site_and_owner_scope() -> None:
    policy = parse_policy(policy_document())
    policies = PolicySet(policy)
    identities = [f"{number:08x}-1111-4111-8111-111111111111" for number in range(105)]
    policies.values = {
        identity: replace(policy, policy_id=identity) for identity in reversed(identities)
    }
    for foreign in (
        replace(policy, policy_id=uid(), tenant=uid()),
        replace(policy, policy_id=uid(), site=uid()),
        replace(policy, policy_id=uid(), owner=uid()),
    ):
        policies.values[foreign.policy_id] = foreign
    tx = Mock(spec=Transaction)
    database = Mock(spec=Database)
    database.transaction.return_value = nullcontext(tx)
    app = InventoryViews(Discovery(database, policies, lambda _: None))
    actor = Actor(policy.tenant, policy.owner, uid(), "inventory.admin", policy.site)

    first = app.read(actor, "policies")
    second = app.read(actor, "policies", cursor=first["next_cursor"])
    third = app.read(actor, "policies", cursor=second["next_cursor"])
    assert [len(page["items"]) for page in (first, second, third)] == [50, 50, 5]
    assert [
        item["policy_id"] for page in (first, second, third) for item in page["items"]
    ] == identities
    assert first["next_cursor"] == identities[49]
    assert second["next_cursor"] == identities[99]
    assert third["next_cursor"] is None
    assert app.read(actor, "policies", cursor=identities[-1])["items"] == []
    tx.execute.assert_not_called()
