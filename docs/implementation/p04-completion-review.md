# P04 completion and native qualification handoff

P04's engineering implementation covers enrollment, bounded read collectors,
observation history, scheduling and Console review. Formal completion follows the
[canonical G04 criteria](gates.md) and requires actual native E3 results and the
specified receiving reviews. The [runbook](../operations/runbooks/inventory-discovery.md)
and [check matrix](../../verification/p04/check-matrix.md) make that work executable.

## Native inputs — BL-P04-001

The platform owners must supply both selected lab installation records. Keep
credentials in approved secret storage and give the collector only mounted
references. No endpoint, version or permission audit has been supplied for these
actual installations; synthetic fixtures cannot fill those fields.

| Input | Required observation |
| --- | --- |
| Installed identity | Exact product/API versions, native installation identity, backend versions, enabled features, entitlements and configuration reference. |
| Scope and trust | Tenant/project or datacenter, site and accountable owner; approved HTTPS origin, literal destination addresses, CA and secret references; independently approved worker identity. |
| Read authority | Restricted credential identity, allowed GET effects, expiry/rotation ownership and independent visibility/permission audit for every required stream. |
| Operating bounds | Approved rate/concurrency and tenant budgets, selected representative cardinalities, collection freshness and test window. |
| Independent observation | Named platform observer, before/after resource identities/state, permission evidence and observation timestamps. |

Once supplied, create the policy using the runbook, enroll it, and run Q02. For each
platform retain source revision, installed tuple, redacted input digests, original
responses/counts, scope, collection timestamps and independent outcomes. Exercise:

1. Complete discovery and rediscovery, checking stable identity and explicit gaps.
2. Partial privilege/pages, incorrect scope, stale facts, lost connection and
   restart, with visible holds and no false empty-success or deletion.
3. Approved shared endpoint and tenant load, retry bounds and recovered freshness.
4. Revocation/renewal, reused identity and conflicting ownership proposals.
5. Independent before/after proof that discovery introduced no native changes.

VMware currently rejects lists above 100 records and exposes no incarnation from
its list API; those are explicit limits, not qualified support. AHV is a profile
contract with an explicit missing collector. Do not expand support statements
without the corresponding adapter and installation evidence.

## Receiving reviews — BL-P04-002

The platform/Inventory, security, SRE, qualification and independent observer roles
review each G04 criterion against the original measurements. Record actual names,
dates, immutable evidence, limits, defects and decisions; development authorization
and automated test results do not supply a review signature.

Product/quality and a representative operator also exercise the Console's tasks:
identify the site/read scope, explain registration versus native write readiness,
distinguish observed from reserved capacity, locate expiry/partial/identity holds,
review a proposed match without assuming ownership, retry an uncertain enrollment
unchanged, and confirm revocation removes protected views. Use the selected browser,
managed policy and assistive technology; record comprehension and accessibility
observations rather than inferring them from automated clicks.

Resolve defects and requalify their affected boundaries, then record G04 in the
delivery register. The next independent implementation work is P05 Planning fact
consumption and stale/partial eligibility, retaining these explicit native holds.
P01/P02/P03 receiving obligations remain visible in `next_work.md`; do not ask again
for the user's already recorded G00 development authorization.
