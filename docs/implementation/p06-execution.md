# P06 — Durable simulation execution

P06 is in active implementation under the existing development authorization.
G06 remains NOT_REVIEWED. No native effects or operational admission are enabled.

The first increment supplies the Lifecycle admission transaction, stable job and
workflow identity, tenant command conflict detection, reservation bindings,
resource/field holds, operation attempts and short-lived one-use grants. A separate
PostgreSQL simulation owner performs effects and sealed readback. Sealing an absent
attempt prevents a delayed old worker from accepting it after reconciliation.
Unknown outcomes, expired grants, revoked authority and custody epoch mismatches
retain allocations and prevent new effects. Cancellation never claims reversal.

The job projection exposes the journal's certainty separately from workflow
progress. Temporal integration, authenticated owner transports, Assurance custody,
Console jobs and the complete real-dependency campaign are the next increments.
The first real-PostgreSQL Q04 campaign is defined in `scripts/p06/`; results must
be retained before claiming verification. Local PostgreSQL startup is unavailable
under this workspace's UID mapping, so database qualification runs on the hosted
Ubuntu runner. No skipped local database test is counted as a pass.
