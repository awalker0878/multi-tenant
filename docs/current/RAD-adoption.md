# RAD-M01 — Reference adoption and deviation design

**Version:** 0.14 · **Status:** Proposed · **Accountable role:** Architecture authority.

## Scope and authority

Reference adoption for enterprise workload mobility and secure hosting across qualified on-premises environments; no site-specific control assessment or production acceptance is implied.

This is a newly authored maintained Markdown record, not a reconstruction of an unavailable Word original. Its creation date is not an acceptance date. Source basis: [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §29](../architecture/reference/29-architecture-decisions-and-alternatives.md).

## Design content

The proposed v1.4 infrastructure reference and delivery-kit v1.1 remain the adoption
basis. Adopt physical/logical views as a versioned set, with independent information
impacts, eligible locations, assurance sharing and explicit exceptions. Tenant
Namespace, WSD, application identity and native domain instance are not synonyms.
An exception records the original requirement, options, route/data/management
consequences, accountable authority and conditions; it does not rewrite source history.

### Workload mobility product boundary

One authenticated control application serves browser and thin CLI operators. The
durable database owns business state and approvals; Temporal coordinates admitted
work, not a second authority ledger. Tenant VPC/domain isolation, commissioned fabric
cells, local overlays, ZIP mediation, shared-service ownership and separated
administration remain architectural boundaries. Native APIs, Terraform and Ansible
realize approved intent behind typed owners; there is one writer per owned resource.

An application comprises observed workloads, datasets, dependencies and reviewed
consistency requirements. A WSD remains its tenant security/placement boundary.
Discovery, a saved application draft, owner assessment and destination comparison
never adopt native resources or authorize their mutation.

### Profiles, security and failure domains

Every selected profile contributes requirements and limitations. The registry has
97 explicit capability dimensions; 28 typed properties distinguish their semantics.
The exact installed product/API/provider/hardware/licence tuple, current evidence,
source preservation requirements and directed route must match. Missing evidence
stays unknown; incompatible observations block. A product name or feature row is not
qualification. Every platform has explicit rows; no tuple is currently native-qualified.

The typed catalog owner rejects missing fields, coercions and unsupported selectors.
Profile validation enforces assurance recovery, workload counts and recovery-zone
composition. Independent-site recovery is refused while its implementation is absent.
Availability catalog 18 corrects the meaning of OZ/RZ/PAZ: security-zone composition
is not proof of separate physical failure domains, reserved restart capacity, automatic
failover or application recovery. No new HA or public capability is enabled.

### Discovery, review and comparison

Signed native reads, original-byte custody, mTLS publication, persisted generations
and scoped normalization are implemented. VMware, AHV and OpenStack have exact enrolled
collector selectors; visible native inventory remains partial. OpenStack selector 2
adds bounded allocation/image/attachment facts without extra endpoint privileges.
Nominal flavor disk sizes do not prove complete transferable storage.

Revisioned application drafts preserve observed membership and attributed assertions.
Independent signed owner decisions are assessment-only and bind an exact draft.
Existing-draft browser editing, CLI save/load/history, review inspection and exact
multi-member comparison are implemented. Report format 2 preserves all members,
selected profiles, source/review/destination pins and explicit unknown/blocker reasons.
Changed drafts, identities or selections invalidate advice and suppress late responses.
Guided initial and saved-revision membership/data/evidence editing, offline owner
signing, exact-draft browser review and custodian intake are also implemented.
Independent dependency verification, deployed owner/key onboarding, owner-to-custodian
transport and administrator acceptance remain open.

Batch staging selects due, already-authorized campaigns under process-local limits.
Shared-outbox capture exclusion and on-demand freshness/history are implemented;
the new checkpointed local schedule adds persisted starts/outcomes, bounded waiting
and original-result reconciliation. It does not establish fleet-wide admission or
periodic alerts. Historical checkpoints are not current authority.

### Migration and acceptance invariants

Migration preserves application outcomes, policy, data/metadata, guest identity,
service dependencies and recovery. Rebuild/restore is distinct from opaque whole-VM
movement. Each directed method needs isolated rehearsal, source-writer exclusion,
final synchronization, controlled exposure and independently observed postconditions.
After target writes, use a reviewed reverse-sync/restore/forward-repair decision;
restarting the old source is not a general rollback. Activation does not authorize
source disposal or address release.

The admitted workflow still returns an authority gate result rather than executing
the complete native provisioning/migration chain. B05 and Wave 2 remain open;
Waves 3–6 are not completed by comparison features or passing local tests. Track
implementation, automated verification, native qualification and operational
acceptance separately under the existing B01–B50 plan.

## Engineering and implementation handoff

The TAD and selected solution inherit the approved baseline version, topology boundaries, sharing choices and service constraints. They identify which fields need actual supported values and which require architecture/security decisions. Independent controls such as physical OOB and key recovery need real owners and design artifacts, not references to an API reader.

Detailed producer/consumer, response, retry and deployment contracts remain at:

- [verified research decisions](../engineering/platform-migration-research.md)
- [application-draft contract](../engineering/application-drafts.md)
- [operator continuation](../engineering/application-draft-operator.md)
- [browser workspace](../engineering/application-draft-browser.md)
- [signed owner-review contract](../engineering/application-owner-review.md)
- [application comparison contract](../engineering/application-comparison.md)
- [installed application-comparison command](../engineering/application-comparison-operator.md)
- [saved-application browser](../engineering/application-comparison-browser.md)
- [bounded batch staging contract](../engineering/discovery-batch-scheduling.md)

See [the current research review](../engineering/platform-capability-review-2026-10-01.md) and
[the B01–B50 execution plan](../product/enterprise-workload-mobility-execution-plan.md).

## Acceptance and open work

Review the explicit scope inventory, current risks and unresolved values. Choose whether this new maintained record meets the service’s documentation need. That owner decision remains open; the repository can validate its completeness of structure, not supply authority.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)
