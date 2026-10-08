"""Each native profile read consumes current authority, a lease and a budget slot."""

from typing import Any

from inventory.application.discovery import Discovery
from inventory.domain.discovery import Rejected, Worker, identifier, number, shape


def authorize_read(d: Discovery, worker: Worker, body: dict[str, Any]) -> dict[str, Any]:
    shape(body, {"discovery_id", "lease_token", "sequence", "request_number"})
    job_id, lease = identifier(body["discovery_id"]), identifier(body["lease_token"])
    sequence = number(body["sequence"], 0, 100)
    request = number(body["request_number"], 1, 52)
    with d.database.transaction() as tx:
        tx.execute("SELECT pg_advisory_xact_lock(7404001)")
        j = tx.one("SELECT * FROM inventory.jobs WHERE id=%s", (job_id,))
        if j is None:
            raise Rejected("not_found", 404)
        e = tx.one("SELECT * FROM inventory.endpoints WHERE id=%s", (j["endpoint"],))
        assert e is not None
        p = d.policy(e)
        if (
            (p.worker, p.worker_fingerprint) != (worker.identity, worker.fingerprint)
            or j["policy_digest"] != p.policy_digest
            or j["endpoint_revision"] != e["revision"]
        ):
            raise Rejected("worker_scope_denied", 403)
        d.collection_authority(p)
        now = d.clock()
        if (
            j["status"] != "running"
            or str(j["lease_token"]) != lease
            or j["lease_until"] - now < 12
            or j["page_count"] != sequence
        ):
            raise Rejected("stale_lease", 409)
        streams = (
            d.configuration_streams(p.streams, p.platform)
            if j["collect_configuration"]
            else p.streams
        )
        stream = streams[j["stream"]]
        limit = (
            8
            if stream["kind"] == "source_profile"
            else 2 + 5 * min(p.max_pages, 10)
            if p.platform == "ahv"
            else 7
        )
        if (
            stream["kind"] not in {"source_profile", "target_profile"}
            or request != j["profile_reads"] + 1
            or request > limit
        ):
            raise Rejected("profile_request_not_admitted", 403)
        if stream["kind"] == "source_profile":
            vms = stream["vm_ids"]
            if j["cursor"] is not None and j["cursor"] not in vms:
                raise Rejected("invalid_profile_cursor")
            index = vms.index(j["cursor"]) + 1 if j["cursor"] is not None else 0
            if index >= len(vms):
                raise Rejected("invalid_profile_cursor")
            pages = tx.all("SELECT payload FROM inventory.pages WHERE job=%s", (job_id,))
            if not any(
                i["kind"] == "server"
                and i["native_id"] == vms[index]
                and i["scope"] == p.native_scope
                for page in pages
                for i in page["payload"]["observations"]
            ):
                raise Rejected("vm_not_in_enrolled_scope", 403)
        # Claim charged the first request. Subsequent GETs share the same endpoint budget.
        if request > 1:
            budget = tx.one("SELECT * FROM inventory.budgets WHERE authority=%s", (p.authority,))
            assert budget is not None
            if budget["next_at"] > now:
                return {"allowed": False, "retry_after": min(2.0, budget["next_at"] - now)}
            tx.execute(
                "UPDATE inventory.budgets SET next_at=%s,last_tenant=%s,"
                "dispatched=dispatched+1 WHERE authority=%s",
                (now + 60 / p.requests_per_minute, p.tenant, p.authority),
            )
        tx.execute("UPDATE inventory.jobs SET profile_reads=%s WHERE id=%s", (request, job_id))
        return {"allowed": True, "retry_after": 0}
