# ICD-M01 — Infrastructure interface ownership and service agreements

**Version:** 0.20 · **Status:** Proposed · **Accountable role:** Producing and consuming infrastructure owners.

## Scope and authority

Producer/consumer obligations across operator, discovery, workflow, native execution, data transfer, evidence and shared-service ownership boundaries.

This is a newly authored maintained Markdown record, not a reconstruction of an unavailable Word original. Its creation date is not an acceptance date. Source basis: [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [NBD §6](../engineering/network-boundaries/6-issue-an-interface-control-and-handoff-record.md) · [SVC §1](../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md).

## Design content

Every agreement identifies producer, actual client, native endpoint, permitted
operation, address family, trust material, entitlement, initiation/reply path, MTU,
capacity and security boundary. Separate data and management ownership. Define
feature/version compatibility, backpressure, finite retries, attribution, key expiry,
recovery order, observer independence and release/retention terms. Shared service
consumption never grants administration of the provider.

### Control-application interfaces

| Boundary | Required binding and hold condition |
|---|---|
| Operator -> API | Verified tenant entitlement, immutable request/plan revision, applicable approval and live revocation. Client parameters are not authority. |
| API -> workflow | Committed job, transactional outbox, exact workflow/run and idempotency identity. Dispatch/gate success is not native completion. |
| Collector -> ingest | Separate enrolled read identity, signed campaign/result, independent credential witness, exact scope and original-byte custody before publication. |
| Worker -> native owner | Approved action/resource, bounded grant, claim and durable intent; uncertain completion prevents blind retry. |
| Native owner -> observer | Exact resource/task/attempt identity and independently observed complete postconditions; echoed requests do not qualify. |
| Source -> transfer worker | Original repository/snapshot/dataset receipt, separate target/root binding, integrity/metadata policy and consistency-group membership. |
| Workload -> service owner | Scoped endpoint/operation, entitlement, reply path and accepted service outcome, not provider privileges. |
| Evidence -> custodian | Original signature/digest/scope/issuer/validity/retention; synthetic tests cannot become site observations. |

These are obligations, not a claim of a fully wired mutation graph. The admitted
workflow stops at its authority gate; target/root and transfer-worker authority
composition remain open. A bounded allocation/lifecycle reference replaces credential
or state dumps. Record expected generation, operation identity and partial-success
stopping conditions before reusing any address, attachment, identity or data copy.

### Versioned profile and capability interfaces

The registry explicitly covers 97 IDs with one digest. Typed property requirements
have exactly `property`, `operator`, `value`, and a required capability owner; integers
exclude booleans. Resolution 3 and policy capsule/realization 2 bind interpretation.
Normalizer 2 and signed findings bind both raw and normalized snapshots; old or changed
interpretations require new review. Comparisons never set execution authorization.
Ten catalog families now use a single typed requirement owner. Required fields,
booleans, integer bounds, relationships and selectors are checked before resolution.
Assurance recovery, workload-count and recovery-zone obligations are enforced once;
independent-site recovery is refused without an implemented composition.

Availability catalog 18 and revised profile entries remove a false equivalence between
security zones and failure domains. Changing catalog identity requires regenerated
examples and fresh plan approval; no HA, public ingress or native support is implied.
A caller provides requirements, not installed support assertions. Support needs an
exact current tuple and independently qualified directed method.

### Native collection contracts

VMware requires `vcenter-rest-vm-info-8.0.3.0-visible-only-2`; AHV requires
`nutanix-ahv-v4.0-hardware-2`; OpenStack requires `openstack-project-https-2`.
Old selectors are not aliases. Native material, campaign root/issuer/collector keys
and independent read-only witnesses have distinct custody. Pinned endpoints/IP/CA,
service identity, validity, API profile, route/response budgets and live rechecks are
mandatory. Returned links and metadata cannot provide new authority or destinations.
Visible and empty native scans remain partial; failed/rotated/revoked reads cannot
publish current observations. Credential issuance and complete visibility remain
site obligations, not consequences of having GET-only code.

OpenStack allocation fields have explicit MiB/GiB-to-byte conversion and signed-64-bit
bounds. Nova relationships are bounded to 64; Cinder attachments to 32 and the existing
8,192-byte fact limit. Unique UUIDs, exact enclosing volume identity and optional bounded
guest device labels are validated. Missing and explicit false/null/empty are distinct.
Flavor root capacity, attachment sorting and deletion flags are not total storage,
boot order, fencing proof or disposal permission. No secrets or arbitrary properties
are imported. Selector changes require matching enrollment/campaign/witness/material,
a new signed generation and reassessment; retained results are not relabelled.

### Original publication, application review and comparison

Stage/publish commands preserve original bytes and explicit delivery. Cooperating
processes share first-capture exclusion; incomplete intents stay held after exit.
Publication retains separate native read and ingest authority. Revisioned draft
save/load/history and bounded browser editing retain source/revision/content pins;
ambiguous saves reconcile by GET. Attributed assertions are not accepted dependencies.
Independent signed owner decisions remain assessment-only and exact-draft bound.
Application report 2 binds every member/profile, canonical selection, source/review,
destination and method/network/data settings. CLI/browser reject mismatched or stale
reports and clear advice after changed selections or identity. No comparison reserves
capacity, transfers ownership or launches mutation.

### Batch, freshness and history interfaces

`hosting-discovery-batch/1` and `hosting-discovery-batch-outcome/1` bind due windows,
protected inputs and ordered outcomes. They declare process-only limits, no durable
schedule, no implicit publication and no execution authority. Queue/deadline limits
cannot replace campaign or credential authority; endpoint aliases/processes require
external coordination. Stop drains accepted bounded work, not remote rollback.
The existing scoped freshness API/CLI distinguish age, MISSING inventory and reported
collection health without inventing visibility. Caller thresholds/generation overrides
are refused. Retained on-demand history adds exact-ID retry, predecessor/cursor checks,
atomic audit and migration 0023/runtime grants. It is not periodic monitoring or alert
delivery. Historical freshness never authorizes collection or mutation.

### Retirement and recovery ownership

Current qualification owners remain in `provisioner.qualification`. Deleted script
owners have no compatibility wrapper. Other writers require freeze/drain/reconcile
and one-time retained-state conversion before removal. Define credential renewal,
lease expiry, unknown outcomes and independent recovery explicitly. Neither producer
may assume another has excluded source writers or admitted target writes; activation
is separate from source disposal, retention release and address reuse.

## Engineering and implementation handoff

Populate the controlled engineering schedule with exact native values and support evidence. Both owners review it. Link each field to the applicable assertion and actual procedure, and retain separately protected evidence. The repository’s examples do not supply those native values.

Detailed producer/consumer, response, retry and deployment contracts remain at:

- [NBD §6](../engineering/network-boundaries/6-issue-an-interface-control-and-handoff-record.md)
- [verified research decisions](../engineering/platform-migration-research.md)
- [native read custody and tests](../engineering/vmware-discovery-https.md)
- [OpenStack read contract](../engineering/openstack-discovery-https.md)
- [the publication and recovery contract](../engineering/discovery-publication-recovery.md)
- [the installed collector contract](../engineering/discovery-collector-runtime.md)
- [application-draft contract](../engineering/application-drafts.md)
- [operator continuation](../engineering/application-draft-operator.md)
- [browser workspace](../engineering/application-draft-browser.md)
- [signed owner-review contract](../engineering/application-owner-review.md)
- [application comparison contract](../engineering/application-comparison.md)
- [AHV HTTPS contract](../engineering/ahv-discovery-https.md)
- [installed application-comparison command](../engineering/application-comparison-operator.md)
- [saved-application browser](../engineering/application-comparison-browser.md)
- [the batch interface contract](../engineering/discovery-batch-scheduling.md)
- [interface contract](../engineering/discovery-freshness.md)

See [the current research review](../engineering/platform-capability-review-2026-10-01.md) and
[the B01–B50 execution plan](../product/enterprise-workload-mobility-execution-plan.md).

## Acceptance and open work

Unassigned endpoints, authority, recovery and version terms block the corresponding handoff. A local draft is not a signed agreement.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)
