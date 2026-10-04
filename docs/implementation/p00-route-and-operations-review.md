# P00 route feasibility and operating review

Review date: 2026-10-04. Scope: P00.04 and P00.05; G00.04 and G00.05. This is a completed desk review and experiment design. Native inventory, application deployment, dataset capture/restore, data recovery, load measurement and owner acceptance have not occurred. The packages remain open in the [delivery register](delivery-register.yaml).

## Findings and current direction

The preferred first migration is VMware → OpenStack using `application_rebuild_restore` for the rebuildable two-workload Linux [Permit Desk application](../product/application-walkthrough.md). This recommendation follows the current P00 method assessment and the user’s clarification on 2026-10-04. It replaces the earlier cold-conversion-first proposal; it is not an automatic inheritance of the old branch’s implementation or status. ADR-014 remains `DESIGN` / `PROPOSED` pending feasibility and accountable review. Whole-VM `cold_guest_disk_conversion_import` remains a separately qualified P09 expansion for workloads that need it. OpenStack provisioning is qualified separately. Laravel service structure, context ownership, current package numbering and the greenfield implementation sequence remain authoritative.

The historical [execution plan](https://github.com/awalker0878/multi-tenant/blob/a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e/docs/product/enterprise-workload-mobility-execution-plan.md) and [migration runtime](https://github.com/awalker0878/multi-tenant/blob/a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e/docs/engineering/application-migration-runtime.md) were read at the pinned `implementation/all-waves` commit `a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e`. The [historical source review](../reference/p00-historical-source-review.md) retains the source-to-current-requirement mapping. Their selected application driver was `REBUILD_RESTORE` for Ubuntu 24.04. The execution plan describes separate cold capture/conversion work while leaving cold target boot and guest remediation open. Neither that implementation nor its test results establish the current route's feasibility. In particular, Ubuntu 24.04, restic transfer and the old runtime owners are not inherited selections for this branch.

Four concrete gaps need resolution before G00.04/G00.05 can pass:

1. No installed source/target tuple or approved fixture is available. A source manifest must identify every application component, dataset, configuration, secret reference and external writer, not merely VM names.
2. Reproducible application deployment, compatible database capture/restore and complete configuration/secret reconstruction are not yet demonstrated. A booted guest and a successful restore command are separate from accepted application behavior.
3. The application outage/data objective and post-target-write recovery method need accountable decisions and a stateful experiment.
4. Existing control-plane target numbers lack an accepted load distribution, measurement denominator and dependency/custody assumptions. The proposed measurement matrix below makes these decisions reviewable.

## Preferred rebuild/restore decisions

These are recommendations for the bounded spike, not selected tool versions, installed facts or native support claims. Rebuild/restore is preferred when the application can be reproduced from known artifacts and its complete state can be captured consistently. An opaque appliance, unavailable dependency or unidentified state can make it unsuitable; do not relabel a whole-VM requirement as satisfied by a rebuild.

| Decision | Recommended next action | Acceptance boundary |
| --- | --- | --- |
| Application reproducibility | Deploy pinned web/database artifacts, guest configuration and required dependencies onto a clean isolated target | Reproduce a usable application without copying undocumented source-machine state; explicitly map required configuration and secret references |
| Data capture and restore | Select a database-aware consistent capture and file/attachment capture covering one declared consistency boundary | A copied live database directory or file checksum alone does not prove application consistency; verify all records, relationships and required metadata |
| Target resource ownership | Create clean OpenStack compute/storage/network resources using the reviewed resource owner; restore datasets through separately journaled operations | Terraform/native infrastructure and data restore must own distinct declared fields/effects; uncertainty holds prevent duplicate creation or restore |
| Guest and application identity | Pin a supported target guest and approved treatment of host, application, certificates, service accounts and licensing identities | Do not inherit Ubuntu 24.04 or old tools by association; test the actual chosen versions and identity-dependent integrations |
| Rehearsal and final cutover | Rehearse with copied synthetic data in quarantine; then quiesce/fence source writers and capture/restore the final consistent state | No production business effects during rehearsal; final cutover binds fresh source state and current authority |
| Recovery | Evaluate target-forward recovery after the first accepted target write; keep source-return as a separate method requiring proven reconciliation | Known accepted target changes must survive; a reachable old source is not sufficient recovery evidence |

## Separate whole-VM expansion

`cold_guest_disk_conversion_import` remains available for P09 design and qualification after its own scope decision. It is not a prerequisite for the preferred first rebuild/restore slice. Preserve these primary-source findings from the 2026-10-04 review for that later work:

- [virt-v2v VMware input](https://libguestfs.org/virt-v2v-input-vmware.1.html) documents different transport constraints. Its VMX-over-SSH path does not support snapshot-bearing guests; direct VMX conversion requires shutdown. A later conversion spike must select a compatible capture/transport rather than issue snapshot consolidation or enable host SSH without separate authority.
- [virt-v2v OpenStack output](https://libguestfs.org/virt-v2v-output-openstack.1.html) describes direct Cinder output from a conversion appliance inside OpenStack and calls its Glance output mode legacy. Cinder output generally needs block-device access. Compare that topology with local conversion and separately journaled import, including exact image/volume ownership, privilege and cleanup.
- [OpenStack image conversion](https://docs.openstack.org/image-guide/convert-images.html) documents disk-format conversion. Our project inference is narrower: format conversion alone supplies no evidence of application correctness, boot compatibility, policy equivalence or recovery.

That expansion must qualify complete disk/backing chains, firmware/controllers/drivers, encryption/vTPM handling, conversion and boot, data correctness, isolation and both recovery boundaries on its own tuple. No conversion dependency was installed or selected by this review, and no converter experiment is required to claim progress on the current rebuild/restore desk work.

## Feasibility input record

Use the field groups below when assembling the candidate record for [the route procedure](../qualification/feasibility/initial-route.md). This is the current input inventory, not a wire schema or a fixture containing invented endpoints. `UNKNOWN` means evidence is absent; `PROPOSED` means a design choice awaits review. An explicit incompatible observation is recorded as `BLOCKED`, separately from an unknown.

Every supplied field group needs `fact_status`, value, source reference/digest, observation time, scope, accountable role and review disposition. Record secret references only; keep native endpoint addresses and sensitive capture locations in the approved restricted record. Schema design must distinguish absent information from false or an empty list.

| Input ID / field group | Required fields and constraints | Current finding | Responsible role / next action |
| --- | --- | --- | --- |
| RT01 `route` | Direction; method; logical application/workload IDs; target environment; fixture revision | `PROPOSED`: VMware → OpenStack; `application_rebuild_restore`; Permit Desk web/database workloads | Product/application owners review method and representative fixture |
| RT02 `source` | vCenter/ESXi builds, API version, endpoint/tenant scope, immutable native VM IDs, observation generation/completeness and permitted reads/effects | `UNKNOWN`: no installed facts or source-operation grant supplied | VMware owner provides read-only inventory and separately scoped lab authority |
| RT03 `target` | Distribution/release and enabled Nova, Glance, Cinder, Neutron APIs; hypervisor/storage/network backends; project, region, failure domains, quotas and feature configuration | `UNKNOWN`: a generic OpenStack label cannot establish boot, security or storage behavior | OpenStack owner supplies supported installed tuple and scoped project facts |
| RT04 `application_and_guest` | Source/target OS, architecture and runtime versions; application/dependency artifacts; database compatibility; service units; required guest/device features; volume/mount mappings; reproducible configuration and secret references | `UNKNOWN`: Linux and web/database roles are directed; distribution, runtime and deployment artifacts remain unselected | Application/platform owners demonstrate clean deployment and identify state or dependencies that cannot be rebuilt |
| RT05 `crypto` | Application/database/backup/volume encryption layers, key and certificate custodians/references, authorized capture access, destination key availability and permitted identity replacement | `UNKNOWN`: absent observations cannot mean unencrypted | Security/key owners classify protected data/configuration and permit the actual restore and identity treatment |
| RT06 `fixture` | Seed/version, database engine/version, schema and dataset list, attachment inventory, expected relationships/digests/metadata, writer list, consistency procedure and correctness queries | `PROPOSED`: synthetic records/attachments only; no supplied fixture bytes | Application/data owner provides reproducible source plus a known post-activation write marker |
| RT07 `network_and_services` | Every NIC and zone mapping; addressing/IPAM/DNS; allowed/denied forward/reply flows; MTU; identity, time, logging, monitoring and backup endpoints; business-effect suppression | `PROPOSED`: OZ web and RZ database with explicit approved dependencies; concrete realization `UNKNOWN` | Network/service owners supply commissioned topology and service contracts |
| RT08 `deployment_and_restore` | Application/guest deployment, consistent database capture, attachment transfer and restore versions/digests; schema compatibility; configuration/secret references; metadata treatment; artifact manifests and operation ownership | `UNKNOWN`: no deployment or backup/restore tool is inherited from history | Engineering/application owners select tools and execute clean deployment plus complete capture/restore experiments |
| RT09 `budget` | Measured deployment/capture/restore throughput, effective transfer rate, staging/backup/target/retained-source bytes, disk attachment limits and tenant/endpoint concurrency caps | `UNKNOWN`: nominal virtual disk size is insufficient | SRE/platform owners measure and allocate bounded resources |
| RT10 `recovery_and_authority` | Quiesce/fence observers, stop/cleanup authorities, first-write proof, outage/data bounds, post-write recovery method, retention/key periods and independent reviewers | `UNKNOWN`: source-return and target-forward procedures require named accountable decisions | Application/platform/security/qualification owners provide scope and signed or otherwise attributable decisions |

## Bounded experiment plan

All cases are **NOT RUN**. Do not create passing results from the expected outcome column. In each executed case retain exact tuple/tool/fixture IDs, approved scope, input/output digests, commands and exit status, independent observations, timings, failures and cleanup disposition. Keep secrets out of logs and evidence exports.

| Case | Setup and observation | Required outcome / failure handling | Downstream coverage |
| --- | --- | --- | --- |
| RF01 Application/state completeness | Reconcile source application components, dependencies, configuration/secret references, datasets and external writers with the deployment/consistency manifest | Every required component and state item is accounted for; an undocumented dependency, omitted attachment store or unhandled identity blocks acceptance | F01/F07; Q07.01 |
| RF02 Reproducible deployment | Build a clean isolated target from pinned guest/application artifacts, recreate approved configuration/identities and apply declared volume/network mappings | The application starts with expected dependencies and identity treatment; no undocumented source-machine copy is required | F02; Q07.02–03 |
| RF03 Application integrity | Capture a declared consistent source point, restore database and attachments, then run exact source/target record, relationship, ownership/permission and consistency checks | Every selected invariant passes; VM boot, a restore exit code or row count alone is insufficient | F03; Q07.03 |
| RF04 Capture/transfer/restore interruption | Interrupt a database capture, attachment transfer and target restore; corrupt one copied chunk; exhaust staging space | No incomplete consistency group becomes activatable; resume/restart follows proven artifact identity and target state, with held resources reconciled | F05; Q07.04 |
| RF05 Restore acknowledgement loss | Lose a create/deploy/restore response after the target may have accepted the effect | Observe native resource identity and actual dataset/restore state; no blind second create or restore and no early allocation release | Q04; Q07.03–04 |
| RF06 Rehearsal isolation | Attempt outbound mail/jobs, undeclared shared-service traffic and cross-tenant access from each target NIC | All prohibited effects fail while required approved service paths work; a network label alone cannot pass | F04; Q06; Q07.02/09 |
| RF07 Unsafe activation | Present stale/revoked authority, a restarted source, active external writer or a missing independent fence observation | Activation is denied and affected work remains visibly held | F06; Q07.05 |
| RF08 Pre-write return | Fail after target validation but before any business write; independently establish target exclusion and absence of divergence | Approved source return restores the application while excluding target and reconciling traffic/service state | F06; Q07.07 |
| RF09 Post-write recovery | Commit a known new target record and attachment; fail the target/control path; execute the selected recovery | New data and relationships survive; retained source remains fenced until reconciled; unproved data preservation keeps the outage/hold | F06; Q07.08 |
| RF10 Restore with stale authority | Restore control-plane state from before target activation/revocation while old worker or source activity may continue | Native writes stay held until actual writer exclusion, current authority, workflow/evidence and native state reconcile | Q04/Q09; P00.05 |
| RF11 Outage, budget and cleanup | Measure the application-level outage and each deployment/capture/transfer/restore/validation interval; inspect retained source, keys and temporary resources | Compare actual values against owner-approved bounds; premature deletion is denied and separately authorized cleanup reconciles every allocation | F05/F06; Q07.09–10 |

RF01–RF03 can establish a bounded method candidate once inputs and lab authority exist. They do not close the complete native Q07 campaign. RF07–RF10 require meaningful state and independently controlled observation/fencing; simulator results can refine implementation but cannot establish site behavior.

## Operating measurement design

The [operating-target document](../product/operating-targets.md) retains the proposed 99.9% monthly control-plane availability, 2-second read p95, 3-second durable-acceptance p95, 15-minute control-plane RPO and 4-hour control-plane RTO. No measured result or owner ratification is recorded here.

For reproducible engineering experiments, propose two synthetic data tiers. These are generator configurations for review, not a forecast of the estate or a production capacity promise. They can be revised before implementation without changing an accepted result, because none exists.

| Dimension | Initial experiment tier | Growth experiment tier | Distribution to retain |
| --- | --- | --- | --- |
| Tenants / applications / logical workloads | 10 / 100 / 200 | 100 / 1,000 / 2,000 | At least one tenant has 50% of workload records; retain empty/small tenants |
| Observed native resources / endpoints | 10,000 / 10 | 100,000 / 50 | Uneven endpoint sizes, one partial generation and revoked/missing-privilege cases |
| Concurrent authenticated sessions | 25 | 250 | Tenant mix, human think time and browser/server request association |
| Journey request mix | 60% reads; 20% status polling; 10% assessments; 10% durable command acceptance | Same mix, then one noisy-tenant burst at twice its nominal offered rate | Valid eligible requests form the objective cohort; record denied/ineligible traffic separately |
| Retained revisions and events | 10 intent revisions per application; event volume generated from the measured command/workflow run | Same revision depth plus a skewed long-history application | Actual bytes, payload size, projection lag and query shape; do not infer event throughput from record count |
| Migration load | One Permit Desk candidate; native effects only within an approved campaign | Concurrency withheld until actual endpoint/transfer budgets are accepted | Dataset size, change rate, staging/retention and bandwidth remain RT06/RT09 inputs |

Use the same admitted security, evidence, encryption and policy behavior as the proposed supported deployment. A small smoke test may precede these experiments but cannot replace their workload distribution. Derive offered requests per second and worker concurrency from accepted endpoint budgets; no native rate is assigned by this document.

| Measurement ID | Instrumentation and calculation | Fault / fairness case | Accountable role and outstanding decision |
| --- | --- | --- | --- |
| OM01 Availability | For each core journey, measure successful eligible events / all eligible events over a defined month; pair production-like probes with request metrics and report low-sample periods | Identity or owning-service failure counts according to the explicitly agreed dependency policy | Product/SRE: approve denominator, maintenance and dependency treatment; the short load run cannot prove a monthly objective |
| OM02 Interactive reads | Correlate browser navigation/action start with usable authorized content; report end-to-end and server p50/p95/p99 plus errors/timeouts by journey and tenant | Noisy tenant, cache cold start, slow dependency and large authorized result set | Console/context owners: set page/input/query limits and timeout classification |
| OM03 Durable acceptance | From valid eligible request arrival to committed acceptance receipt; observe recovery after process failure around commit/response | Lost acknowledgement, duplicate request, queue pressure and delayed outbox delivery | Lifecycle/SRE: define admitted request rate and stable idempotency checks; do not time only the HTTP handler |
| OM04 Discovery and queues | Age since last complete authorized generation; oldest eligible message age; depth and per-tenant service share | Partial pagination, endpoint throttling, one failing endpoint and a noisy tenant | Inventory/platform owners: select per-class freshness and native call/concurrency budgets |
| OM05 Control-plane recovery | Measure recoverable committed-state gap across required stores; time incident declaration to safely reviewed service, separately reporting write resumption | Lost key access, evidence-store interruption, site partition and restored stale workflow/approval state | SRE/security: select backup/restore topology, effective fencing and key custody; retain recovery holds even if RTO expires |
| OM06 Application migration/recovery | Last valid source service to first accepted target service, first target-write timestamp, known-write/data diff and actual retained source/target state | RF08 pre-write return and RF09 post-write recovery | Application/data owners: choose outage, loss and post-write recovery bounds; control-plane RPO does not cover application data |
| OM07 Evidence and alert delivery | Time effect observation to durable bound evidence receipt and signal to receiving on-call acknowledgement | Receiver outage, duplicate alert, missing object/key and delayed finalization | Assurance/on-call/security: set evidence/alert objectives, recipients and escalation; log emission alone is not delivered alert evidence |

For OM02/OM03, preserve offered/completed request counts and raw timing/error distributions. Do not discard timeouts from the reported workload or combine tenants in a way that hides starvation. Record generator clock method, warm-up and sampling duration in each run; at least three repeat runs are a proposed reproducibility check, not independent statistical proof of service availability.

## Trust and recovery inputs for P00.05

The existing [threat model](../operations/threat-model.md) and [recovery procedure](../operations/runbooks/recovery.md) already require current authority, effective old-writer exclusion and reconciliation before resuming native changes. This review adds the following concrete acceptance observations to OM05–OM07; it does not change the chosen context boundaries.

| Loss or trust boundary | Required observation before resumption | Input still required |
| --- | --- | --- |
| Site worker loses the control plane | No new privileged effect starts without the current scoped authority required by the selected disconnection policy; dispatched effects retain true known/unknown state | Site transport, revocation reachability, effective fencing mechanism and operating owner |
| IdP/PKI or signing key is unavailable/revoked | Service/worker identity and post-backup revocations are independently current before acceptance or native writes resume | Selected trust providers, rotation/expiry rules, custody, recovery access and test authorities |
| Evidence object store or encryption key is lost | Evidence bytes/digests and readable key scope reconcile with owning records; missing proof keeps affected completion/qualification held | Custody/location, retention, independent recovery copy and key restoration controls |
| Restored workflow state predates accepted target writes | Source/target writer and known-write markers reconcile before any replay/resume action; no source restart from stale state | Selected engine/store restore points, native observer and post-write application recovery method |
| Support operator requests sensitive capture/log access | Access is attributable, time/scope bounded and reviewed; protected payload and secrets stay in permitted locations | Classification, permitted locations/support personnel, retention and records-owner decision |

## Finite input handoff and next executable work

No actual owner identities, lab addresses, credential grants, fixture bytes or target ratifications were supplied. The responsible roles below remain roles to assign, not approvals. The delivery register owns formal blocker status and next actions; this table defines the concrete missing inputs.

| Input request | Minimum response that unblocks work | Blocked scope |
| --- | --- | --- |
| RI01 Installed tuple | RT02–RT05 source/target/application/guest/key observations and exact supported APIs/backends | Selecting compatible deployment/capture/restore tools and interpreting RF01–RF03 |
| RI02 Fixture and data objectives | Reproducible Permit Desk seed, database choice, complete dataset/writer manifest, correctness queries, outage/loss bounds and known target write | RF03/RF08/RF09 and application acceptance |
| RI03 Lab authority and observers | Named source/target/security owners, isolated permitted resources/effects, limits/window, stop/cleanup authority and independent fence/readback path | All native experiments; documentation work confers no site permission |
| RI04 Topology and capacity | RT07/RT09 network/service realization, effective bandwidth/storage/attachment budgets and approved target ownership | RF02/RF04/RF06/RF11 and native concurrency settings |
| RI05 Recovery and custody decision | Selected post-write method; source retention/key rules; current trust, support/custody and restore model | RF08–RF10, OM05–OM07, G00.05 acceptance |
| RI06 Operating target review | Accept or replace tier numbers and objective measurement/denominator rules; assign accountable people and independent reviewers | Ratifying ADR-017 and reporting any accepted capacity/SLO claim |

Independent work completed: historical/current method comparison; current rebuild/restore recommendation and feasibility design; retained primary-source constraints for separate P09 whole-VM work; input inventory; bounded positive/negative/recovery experiment design; proposed load tiers and measurement definitions. Continue schema/fixture-generator design and compatibility work under the current phases while requesting RI01–RI06. No native command is authorized or claimed by this review, and no P00 gate passes from documentation alone.
