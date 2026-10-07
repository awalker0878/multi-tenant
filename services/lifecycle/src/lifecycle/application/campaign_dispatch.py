"""Restart-safe campaign admission. A scheduled item is never a cached native grant."""

from collections.abc import Callable
from typing import Any

from lifecycle.application.campaigns import Campaigns
from lifecycle.application.native_workflow import NativeWorkflow
from lifecycle.domain.execution import Rejected


class CampaignDispatcher:
    def __init__(
        self,
        campaigns: Campaigns,
        native: NativeWorkflow,
        plans: Callable[[str, dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.campaigns, self.native, self.plans = campaigns, native, plans

    def tick(self, maximum: int = 32) -> dict[str, int]:
        if type(maximum) is not int or not 1 <= maximum <= 100:
            raise Rejected("campaign_dispatch_bound", 422)
        with self.campaigns.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(7707002)")
            pending = tx.all(
                "SELECT m.id,m.tenant,m.campaign,m.specification FROM app.migration_members m "
                "JOIN app.migration_campaigns c ON c.id=m.campaign "
                "WHERE m.state='queued' AND c.state='scheduled' ORDER BY "
                "m.considered_order,(m.specification->>'priority')::integer DESC,"
                "c.created_at,m.ordinal LIMIT %s",
                (maximum,),
            )
            for member in pending:
                tx.execute(
                    "UPDATE app.migration_members SET considered_order="
                    "nextval('app.migration_dispatch_order') WHERE id=%s",
                    (member["id"],),
                )
        counts = {"admitted": 0, "waiting": 0}
        for member in pending:
            tenant, campaign, key = (
                str(member["tenant"]),
                str(member["campaign"]),
                str(member["id"]),
            )
            try:
                # Skip expensive owner reads while an immutable schedule/resource hold applies.
                with self.campaigns.database.transaction() as tx:
                    self.campaigns.eligible(tx, tenant, campaign, key)
                plan = self.plans(tenant, member["specification"])
                self.native.admit(plan, key, (campaign, key))
                counts["admitted"] += 1
            except Rejected as error:
                counts["waiting"] += 1
                with self.campaigns.database.transaction() as tx:
                    tx.execute(
                        "UPDATE app.migration_members SET reason=%s WHERE id=%s "
                        "AND tenant=%s AND state='queued'",
                        (error.reason, key, tenant),
                    )
            except Exception:
                counts["waiting"] += 1
                # Never repeat a provider operation here. Native admission has a durable key.
                with self.campaigns.database.transaction() as tx:
                    tx.execute(
                        "UPDATE app.migration_members SET reason='campaign_owner_unavailable' "
                        "WHERE id=%s AND tenant=%s AND state='queued'",
                        (key, tenant),
                    )
        return counts
