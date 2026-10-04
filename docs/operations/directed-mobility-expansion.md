# Directed mobility and bounded wave scheduling

The installed application path is VMware NSX to OpenStack, application rebuild
and restore, with the exact `linux-ubuntu-2404` guest profile and
`openstack-linux-rebuild/1` driver. Installation does not qualify a native
migration. The current qualification and operating owners must admit every
selected action before a native writer can run.

## Expansion evidence

`provisioner.qualification.directed_mobility` declares installed implementations
and adds method procedures to the existing mobility campaign owner. It does not
create another evidence index. A dossier must retain its exact source and
destination product tuples, selections, direction, method, guest profile, lab
workload/job/plan, code revision and installed artifact digest. Reversing a route,
changing an OS release, or selecting another method requires separate evidence.
Complete synthetic dossiers cannot supply missing installed owners.

| Direction or method | Current boundary |
| --- | --- |
| VMware NSX to OpenStack, application rebuild/restore, Ubuntu 24.04 | Implemented driver path; requires separately accepted current native and operating evidence. |
| Other rebuild directions or guest releases | Held for the exact directed application/guest implementation. A broad Linux category conveys no release support. |
| Cold whole VM | Capture/export, disk-chain capture, target import/boot and qualified guest remediation remain missing. Only retained-descriptor inspection is available. |
| Same-family relocation | Qualified topology move, device/key lineage and interrupted native-task recovery remain missing. |
| Application-native database synchronization | Selected engine/version driver, commit-position cutoff and divergent-writer/reverse-sync owners remain missing. |
| Warm whole VM | Convergence/stop control and RAM/device/key preservation remain missing. |

The existing campaign gate checks method-specific positive procedures and
negative controls with independent positive-control proofs. The selected-action
gate also checks the declared installed route. Unsupported combinations remain
held even when every evidence field is populated.

## Retained cold-image inspection

Parse `hosting-vmware-openstack-cold-descriptor/1` using
`ColdCaptureDescriptor.from_record(record, campaign, plan)`. The descriptor must
bind the canonical plan and source snapshot, exact VM and complete selected disk
IDs, guest firmware/controllers/devices, immutable standalone disk byte extents
and digests, writer fence and quiescent native-task declarations. Unknown power
or task state, incomplete chains, encrypted or shared disks, passthrough devices
and unsupported guest/boot profiles produce holds before disk parsing.

`inspect_retained_disks` only inspects protected retained disk files. Its output
parent must already be private commissioned storage. The image owner copies the
checked byte extent into an exclusive protected input, verifies its digest,
executes bounded `qemu-img info` in the required isolated sandbox, then verifies
the retained input again. Sandbox/tool absence is a hold. Inspection performs no
capture, conversion, import, remediation, boot or native write; descriptor
declarations are not authenticated capture evidence.

## Wave planning and admission

`provisioner.migration.wave_schedule` schedules within one tenant and one
independently enrolled native-domain budget. Fairness is round robin across the
currently authorized source workload security domains, then oldest schedule and
member. Splitting one security domain across schedules does not buy more turns.
Cross-tenant global fairness and authenticated multi-host transfer pools remain
open. Local stage, block-device, cgroup and target-root identities conservatively
share one commissioned worker-host resource owner.

An enrolled `WaveDomain` binds exact native scopes, shared failure-risk groups,
independent native-budget evidence and a finite observation lifetime. Alternate
site/security-domain labels cannot enroll the same physical native scope into
another budget owner. Domain documents are immutable.

| Budget | Demand retained until accepted release |
| --- | --- |
| Concurrent jobs and exposed workloads | One of each per admitted member. |
| Downtime seconds | The approved maximum downtime, independently of transfer duration. |
| Aggregate risk and each shared-risk group | The member's explicit conservative risk units. |
| Download rate, block IOPS and staging bytes | Sum of every actual protected dataset transfer descriptor. A capacity receipt cannot authorize transfer throughput. |

`WaveMember` retains its exact immutable canonical production plan, dependency
IDs, UTC window, complete conservative runtime, risk and actual transfer limits.
`WaveDefinition` rejects cycles, duplicate plans/workloads, absent dependencies
and tenant/domain mismatches. Its sorted canonical content produces an immutable
schedule digest and `wave-<digest>` reference; a saved definition issues no
approval, job, grant or native command.

Use the trusted service owner's three operations:

1. `register(credential, context, definition)` requires current human workload
   editing authority for every exact source and destination security domain. It
   reloads persisted plans/workloads and derives native and actual transfer
   overlap identities; caller-supplied overlap labels are not accepted.
2. `admit_next(credential, context, domain_id, authorizations=...)` requires a
   fresh actor-specific approved plan for the selected member and current
   execution authority for both scopes. Under one database domain lock it
   checks dependencies, fairness, every budget, resource overlap, complete
   window and the current qualification bundle. It commits the normal B09 job,
   outbox, wave member, resource claims and journal atomically. It starts no
   workflow and reports `JOB_QUEUED`, never completed migration.
3. `reconcile_release(credential, context, schedule_digest, member_id)` consumes
   a separately accepted current native release. It never authors acceptance.
   Without that acceptance, charges and overlaps remain held.

The selected qualification campaign retains its original lab plan/job
provenance. It is not rewritten to match a future production member. Current
native route/action evidence admits the exact direction/method/profile/product
tuples/code/artifact, while B09 independently binds the production plan and
current approvals. The current five-index bundle and protected execution/data
selections are reloaded at admission.

Future windows wait. A window without enough time for the full remaining runtime
is held. B09 start and current native authority checks revalidate the exact
affiliated member window; delayed starts and later effects cannot inherit an
expired window. Job admission, terminal projections, timeouts and uncertainty
never release native claims or mark a dependency complete.

## Database roles and release acceptance

Migration `0027_migration_wave_schedule.sql` applies forced tenant row security,
immutable planning/event records and guarded member/claim transitions. It grants
no privileges to `PUBLIC`. Configure distinct commissioner, runtime, site-worker
and operating/reconciliation reviewer credentials:

| Principal | Narrow wave permissions |
| --- | --- |
| Commissioner | Insert/select enrolled domains and their scope projection. No runtime enrollment path. |
| Runtime | Select domain/scope/release facts; select/insert waves/events; select/insert/update members/claims. Execute the three service helpers below. No domain or release-acceptance insert. |
| Site worker | Execute only the exact-job window helper; no schedule mutation or raw enumeration. |
| Independent reviewer | Insert the separately reviewed release acceptance. Its trigger reads protected native facts as the tenant-constrained migration owner; the reviewer needs no private-helper execute or containment-table read. |

Exact public service helper signatures are
`lock_migration_wave_domain(text,text,text)`,
`migration_wave_job_window(text,text,text)` and
`migration_wave_release_is_current(text,text,text,text,timestamptz)` in
`hosting_controlplane`. All verify authenticated tenant scope; the job helper
also verifies a site credential's existing exact-job visibility. Private release
validation and trigger functions retain revoked public execution and fixed
search paths.

A release acceptance binds the original admitted job and plan, delivered
workflow start payload/run, exact terminal event/evidence, and independent
transfer-stop, owner-exclusion and cleared-shared-risk receipts. Its guard rejects
missing native inventory, unresolved operations, non-quiescent or superseded
observations, containment and stale acceptance. Each operation needs its latest
independently quiescent observation and exact resolution evidence. Successful
release must also follow completion within the approved window. The scheduler
then releases all charges and claims atomically. Current implementation tests do
not constitute native release evidence.

## Qualification and checks

`WaveDefinition.run_sheet()` binds `controlled-migration-wave:<scheduleDigest>`
to each actual member plan digest and separately retained qualification variant.
Run the dependency-order, concurrent-budget-stop, shared-risk-containment and
scope-fairness procedures on the commissioned native path. Concurrent wave
evidence is distinct from single-application evidence; retain direction and
method separately. Global cross-tenant fairness needs its own future owner and
campaign.

Run local checks with `python -m unittest discover -s
tests/provisioning/mobility`. PostgreSQL cases require the isolated test database,
`HOSTING_TEST_POSTGRES_DSN`, `HOSTING_TEST_POSTGRES_MIGRATION_DSN` and
`HOSTING_TEST_POSTGRES_ISOLATED=1`; missing configuration explicitly skips them.
Those cases exercise concurrent admission, atomic rollback, dependency/risk
holds, fairness, windows, current approval, tenant isolation, forbidden runtime
enrollment/release writes and missing-native-inventory refusal. Genuine native
campaigns, independently accepted release and final expansion qualification
remain required.
