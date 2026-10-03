# TAD-M01 — Technical infrastructure composition

**Version:** 0.29 · **Status:** Proposed · **Accountable role:** Platform, network and security engineering.

## Scope and authority

Technical decomposition of the control application, durable authority, discovery, provisioning and migration paths together with fabric, native stacks, security edge and shared services.

This is a newly authored maintained Markdown record, not a reconstruction of an unavailable Word original. Its creation date is not an acceptance date. Source basis: [RA §3](../architecture/reference/3-system-context-and-physical-hosting-topology.md) · [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [RA §15](../architecture/reference/15-cross-vendor-realization-model.md) · [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md).

## Design content

Compose commissioned fabric capacity, native platform domains, scoped security edge
and service attachments behind the control application. Physical OOB, administration,
tenant data paths and service consumption remain separate; an overlay alone does not
supply security intent or service acceptance. The LLD binds these boundaries to actual
supported site values, not fixture addresses.

### Control application and durable authority

PostgreSQL tenant isolation, immutable business/audit records, OIDC/IAM provenance,
independent approvals and transactional admission/outbox bind accepted work to a plan
revision and exact workflow/run. Temporal provides durable execution/replay and build
routing. Enrolled workers receive bounded grants; resource claims, durable native
intents and fresh per-effect authority checks prevent competing writers. Reconcile
accepted work after revocation; an unknown outcome is held, never blindly retried.
`AdmittedMigrationJob` currently completes its authority gate only.

### Native discovery and original evidence

The installed collector composes three exact read-only profiles:

| Platform | Collector selector | Native read boundary |
|---|---|---|
| VMware | `vcenter-rest-vm-info-8.0.3.0-visible-only-2` | Reviewed folders and list-derived VM detail; captured visible set, not invented native paging. |
| AHV | `nutanix-ahv-v4.0-hardware-2` | Pinned VMM v4.0 VM reads and typed boot/device facts. |
| OpenStack | `openstack-project-https-2` | Exact project Nova 2.79, Cinder 3.60 and Neutron v2.0 roots; no automatic version fallback. |

Native material is independently signed and bound to campaign, environment, credential
reference, service identity, TLS origin/IP/CA and validity. Current campaign enrollment
and native read-only witnesses remain independent checks. The common HTTPS owner
constrains routes, headers, framing, JSON size, paging and deadlines. Authority is
rechecked around waits, transport and publication. No redirects, arbitrary URL
following, credential issuance or privileged fallback are supplied by the collector.
Successful native lists remain partial/visible-only, including empty lists.

OpenStack selector 2 retains strict embedded vCPU/RAM allocation, nominal root,
ephemeral and swap quantities, image references, attached-volume IDs and native
delete-on-termination booleans. Cinder attachment/server/volume identities and optional
guest device labels are bounded and canonical. Missing fields stay unknown; explicit
false/null/empty observations remain distinct. Nominal flavor disk capacity is not
total disk capacity; sorted identities do not establish boot order or writer exclusion.
Only whitelisted fields survive. No extra read route or native privilege was added.
The first selector is retired with no forwarding alias; new enrollment, evidence and
review are required rather than relabelling existing signed results.

Original campaign/result signatures are retained before authenticated publication.
The installed stage/publish commands, restart custody and shared-outbox first-capture
claims reuse that authority. Exact retries retain original bytes; interrupted first
captures remain held. This is cooperating-process custody, not a distributed scheduler.

### Profiles and useful comparison

Registry format 2 binds the 97-capability vocabulary; 28 typed properties and their
digest qualify semantics beneath those IDs. Every selected family contributes
capabilities, constraints and limitations. Resolution format 3 and policy
capsule/realization format 2 reject older interpretations rather than translating them.
`provisioner.profiles.requirements` is the single field/type owner for all ten families;
`profiles.validation` owns assurance recovery, workload-count and recovery-composition
checks. The redundant semantic recovery branch and parallel field table are removed.

Availability catalog 18 describes security-zone composition, not native HA. Physical
failure domains, restart reservations, monitoring behavior and service recovery need
separate observed and qualified evidence. Deferred profiles remain refused. The five
reference requests across three platforms are regenerated for changed digests and
remain disabled. Approved plans require reassessment under the new catalog identity.

Normalizer 2 preserves raw and normalized generation pins. Signed installed-tuple,
directed-route and control evidence feed scoped comparisons; neither another cluster's
properties nor a platform-wide flag can fill missing selected-pool observations.
Whole-VM compatibility checks hardware, boot, key, driver, shared-device and writer
requirements; warm-transfer comparisons check measured convergence assumptions.
These are comparison prerequisites, not conversion or data movement implementations.

### Application review and operator composition

Immutable drafts retain observed VM membership, datasets, assertions and expected
revision. Saves use cooperative generation locking and exact retry/content semantics;
uncertain saves reconcile through reads, not unguarded replay. Separate signed owner
assessment decisions preserve exact draft/source pins and current reviewer authority.
The existing browser component now creates initial proposals using exact-generation
VM choices, explicit dataset groups and known/unknown dependency forms. It reuses the
same API, shared proposal validator and uncertain-save reconciliation owner; first
writes use expected revision zero and reconcile exact revision-one history. Source
summaries, names and proposed evidence are not independent acceptance. The same editor
now explicitly revises saved membership, dataset groups and dependency assertions.
Entry rechecks the exact saved source; an isolated working copy preserves original
order/precision, and saves require loaded revision N with exact N+1 acknowledgement.
No rebase or owner-review reuse is permitted. Failed source reads disable editing and
comparison; uncertain writes reconcile exact history. An installed offline owner command
now prepares the existing assessment envelope from a full digest-pinned draft export,
then signs explicitly confirmed canonical bytes. The existing trust owner checks exact
root-enrolled owner/scope/key eligibility before signing and verifies the signature
again before create-only private-file publication. No private key enters the portal or
operator client. Export checksums do not establish server currency: the existing ingest
repository independently checks the retained draft, current source and live trust.
The draft workspace now presents exact-revision signed-review status through the
existing read API. It shares one browser wire validator with application comparison;
that component no longer maintains a duplicate review interpretation. Returned scope,
record/proposal/source digests, owner/editor separation, UTC microseconds and status
precedence are checked. The view is evaluated-at-time advice, clears on edits, changed
identity/selection and hidden tabs, and schedules bounded display clearance. Timers
are not a current-authority guarantee. A reported superseded source/draft prevents
editing or comparison until current reload, without rewriting the retained record.
Owner/key provisioning, authenticated delivery, independent external evidence and
enterprise/administrator acceptance remain open. Signing is assessment-only, never
native ownership or migration approval.
Application comparison report 2 binds canonical selection, every member profile,
source/review references, destination pools and method/network/data modes. Mismatched,
stale, partial or contradictory responses cannot become positive advice.

### Scheduling, freshness and retained history

Bounded batch staging uses protected manifest/config digests and due windows. Optional
private checkpointing persists starts before collection, waits for already-enrolled future
tasks and reconciles only original signed-outbox results after uncertainty; it cannot mint
campaigns, publish implicitly or claim global endpoint limits. Endpoint admission remains
local to cooperating processes and durable fleet scheduling remains open. Freshness
inspection separates capture age from collection health and visibility. The scoped API/CLI,
on-demand writer, retained history and deterministic periodic evaluator are implemented.
Stable target/time-slot IDs make restarts idempotent against retained checks. Digest-bound
warning/critical alert intents are projections only: notification delivery, acknowledgement,
deployed service scheduling, global admission and independent visibility reconciliation remain
open. Migration 0023, narrow grants, atomic audit and predecessor/cursor integrity remain the
history owner. Freshness is not qualification.

### Provisioning, transfer and recovery boundaries

The required chain is reserve -> prepare -> saved plan -> independent review/approval
-> apply -> observe -> power/readiness -> guest -> services -> controlled activation.
Existing native lifecycle/readback, fenced power and guest/service handoffs do not
complete that admitted durable chain. Commissioning includes DNS, identity, time,
trust, logs, monitoring and application-consistent backup/restore with owner receipts.

Transfer retains original source receipts, exact canonical dataset coverage and complete
consistency-group joins. An independently observed target dataset/root, trusted mTLS
worker-to-authority binding, qualified attempt credentials and old-writer exclusion
remain missing composition. `targetRef` is neither native ID nor filesystem path.
Durable transfer identity is separate from expiring attempt grants. Final sync, source
fencing, traffic switch and post-write recovery are not closed by integrity contracts.

### Runtime and verification ownership

The WSD compiler and qualification registry/native/provenance owners are package-owned;
retired entry points stay deleted without aliases. Other actively imported top-level
owners and retained-state conversion keep B05 open. Move each real consumer and its
state before deletion; do not remove functional safety adapters as shims. Installed
wheel/sdist checks must run outside the checkout. Unit/loopback tests, real database
integration, installed execution, native campaigns and operational acceptance remain
separate evidence classes on the final artifact revision.

### Signed owner artifact intake

The installed custodian intake now submits a canonical owner-signed artifact to the
existing assessment repository under one configured environment/scope. It shares
private-file handling with the offline signer, uses a dedicated authenticated SQL
login with forced-RLS/privilege checks, and rechecks inputs/trust before commit.
Create-only local receipts distinguish confirmed ingestion from uncertain commit or
receipt publication; they are not current owner reviews or migration grants.
Owner-to-custodian transport and deployed TLS/SCRAM/custody qualification remain open.

See the [custodian intake contract](../engineering/application-review-intake.md).


The Terraform catalog implementation is now package-owned at
`provisioner.execution.terraform_catalog`; every in-tree consumer migrated and the
old tools module is removed without an alias. The reader validates finite JSON,
canonical source paths, local root/module ownership and the registered source set.
Existing catalog/configuration/plan bytes remain unchanged. Clean build staging
removes deleted Python owners and bytecode; source-overlapping output is refused.
Installed tests load the reader from bundled resources with legacy imports blocked.
This does not convert state, renew old source-bound approvals or close other B05
runtime owners. See the [catalog runtime contract](../engineering/terraform-catalog-runtime.md).

### Checkpointed discovery scheduling

The existing batch dispatcher now optionally uses a private digest-linked journal
owned by `batch_journal.BatchJournal`. Starts are retained before stage, and one local
schedule invocation can wait for already-enrolled due work within a bounded horizon.
Crash recovery never recollects an uncertain task; reconciliation accepts only the
original signed outbox object under the same immutable campaign/configuration binding.
Completed checkpoints are historical, not current inventory or publication receipts.
No new API/SQL role is introduced. Global fleet budgets, periodic monitoring/alerts,
external restore high-water marks and operating acceptance remain open.

See the [checkpointed scheduling contract](../engineering/discovery-checkpointed-scheduling.md).

### Package-owned reservation evidence

`provisioner.allocations.reservation_evidence` now owns the exported reservation
record reader used by repository access, reservation preflight and IPAM parent checks.
It validates bounded regular input, duplicate/nonfinite JSON and contained source
references while retaining record/schema/digest and expiry/uncertainty semantics.
Installed checks prohibit legacy imports and working-directory fallback. This is not
a new writer or reservation service; B23 transactions and remaining B05 owners stay
open. See the [runtime contract](../engineering/reservation-evidence-runtime.md).

## Engineering and implementation handoff

The LLD supplies actual native identities, interfaces, addresses, limits, support evidence, privilege scopes and code artifacts. P0–P6 assigns one resource writer per lifecycle scope. Terraform roots, supported installers, service-owner integrations and Ansible procedures consume accepted handoffs without sharing unrestricted credentials.

Detailed producer/consumer, response, retry and deployment contracts remain at:

- [verified research decisions](../engineering/platform-migration-research.md)
- [native read custody and tests](../engineering/vmware-discovery-https.md)
- [the AHV read contract](../engineering/ahv-discovery-https.md)
- [OpenStack read contract](../engineering/openstack-discovery-https.md)
- [the publication and recovery contract](../engineering/discovery-publication-recovery.md)
- [the installed collector contract](../engineering/discovery-collector-runtime.md)
- [application-draft contract](../engineering/application-drafts.md)
- [operator continuation](../engineering/application-draft-operator.md)
- [browser workspace](../engineering/application-draft-browser.md)
- [signed owner-review contract](../engineering/application-owner-review.md)
- [offline owner preparation/signing contract](../engineering/application-owner-signing.md)
- [exact-draft browser review contract](../engineering/application-review-browser.md)
- [application comparison contract](../engineering/application-comparison.md)
- [installed application-comparison command](../engineering/application-comparison-operator.md)
- [saved-application browser](../engineering/application-comparison-browser.md)
- [batch contract](../engineering/discovery-batch-scheduling.md)
- [freshness contract](../engineering/discovery-freshness.md)

See [the current research review](../engineering/platform-capability-review-2026-10-01.md) and
[the B01–B50 execution plan](../product/enterprise-workload-mobility-execution-plan.md).

## Acceptance and open work

Missing native edge construction, platform commissioning, actual IAM/backup/key integrations and tested failure behaviour stay open. Record accepted operation coverage for create/observe/update/adopt/replace/delete and uncertain completion; a valid plan is not a TAD acceptance.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)
