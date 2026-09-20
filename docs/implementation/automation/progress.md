# Automation implementation progress

**Updated:** 2026-09-20. **Release status:** incomplete; no native platform is qualified by this change. The former `docs/1.0` material is now maintained under engineering, implementation and assurance. The [baseline audit](../../assurance/automation-baseline-audit.md) and its evidence remain historical. Every W01–W29 acceptance package is still open under its [original closure criteria](completion-backlog.md).

## Delivered changes

| Change | Main commit | What is implemented |
| --- | --- | --- |
| Promote the 1.0 documentation | [bf46146](https://github.com/awalker0878/multi-tenant/commit/bf461469d4dc6b1b294d366e6b709d21ad190be7) | Maintained engineering topology, implementation program and assurance audit; repaired links |
| Separate Terraform execution roots | [86105dc](https://github.com/awalker0878/multi-tenant/commit/86105dc8f47cbe5f4bfde021e9ff299b69337911) | `stacks/components`, explicit catalogue, dynamic engine scope discovery; existing component addresses preserved |
| Compose WSD domains and workloads | [79aa0f0](https://github.com/awalker0878/multi-tenant/commit/79aa0f03d3762e9461dd6d9150fbf2c961ed2571) | Six typed compositions and separately owned roots for Nutanix, VMware/NSX and OpenStack; real schema checks and plan-only mocks |
| Update the command-boundary regression | [a6c253a](https://github.com/awalker0878/multi-tenant/commit/a6c253a9f5c071918ec749b23d0b3ca17157ae59) | Backend-free module/composition checks replace the remaining fixed-directory/count assumption |
| Compile cluster placements and output handoffs | [fe08ce4](https://github.com/awalker0878/multi-tenant/commit/fe08ce4e80dfe5d0635716326cc7aa6941bd04bc) | Two-tenant/four-domain examples, role/zone/trust/dedication checks, scoped state identities, disabled draft inputs and matching native output IDs |
| Separate local Ansible profiles | [0c56fb9](https://github.com/awalker0878/multi-tenant/commit/0c56fb9556032109a03a78fe9155557bd234a8e1) | `playbooks/local`, three-platform no-contact manifest validation, real local idempotence/check-mode tests |
| Bind native Linux guest execution | [56e1124](https://github.com/awalker0878/multi-tenant/commit/56e1124afe1c6c1b560b14592f1256c867d0aec8) | Private inventory from workload IDs, pinned SSH keys and observed machine identity; serial Ubuntu 24.04/chrony candidate role with pre-contact guards |
| Correct packet-lab host comparison | [9a76d90](https://github.com/awalker0878/multi-tenant/commit/9a76d908661780bc0126faf25c9f9873b054adec) | Both campaigns compare normalized full host configuration; ordering/lifetimes/counters do not imply drift; addresses/routes/MTUs/forwarding remain checked |
| Tighten private input and guest check mode | [15a574d](https://github.com/awalker0878/multi-tenant/commit/15a574d5eef482ab4ad957e7e8131ff53646d762) | Duplicate JSON keys and non-finite values rejected; live kernel drift explicitly reported in check mode |

Use the [WSD deployment runbook](wsd-deployment.md) and [native guest runbook](native-guests.md) for the actual interfaces, private inputs, output binding and migration precautions. No native apply, guest connection, state migration, activation, deletion or infrastructure deployment was executed during this implementation.

## Reviewed execution increment

[PR #46](https://github.com/awalker0878/multi-tenant/pull/46) delivers the next
repository implementation in separate commits. Its [execution runbook](terraform-execution.md)
documents the supported operator path and its remaining integration boundaries.

| Delivered capability | Concrete behavior | Remaining boundary |
| --- | --- | --- |
| Private saved-plan preparation | Clean source snapshot, pinned Terraform, explicit HTTP lock endpoints, current contact authority, exact input/credential/trust binding and the existing restricted-plan review | Actual backend, native credentials, accepted target and engineering approval remain external |
| Exact-plan application | Exact bundle/review binding, live expiry checks, backend lock, private logs and source-bound execution | The issuing authority and actual target qualification are not created by JSON records |
| Durable attempt ledger | Persist uncertainty before mutation; reject duplicate operation/generation, concurrent executor writer and unknown prior outcome | A shared durable ledger is required; native tasks and other tools require actual fencing and reconciliation |
| Three-platform credential path | Nutanix/VMware injected credentials; self-contained scoped OpenStack cloud profile; bound optional private CA | Actual least-privilege credentials and supported installed tuples must be supplied and qualified |
| Receipt-based handoffs | Successful exact domain outputs compile disabled workload drafts; successful workload receipts feed pinned guest inventory | Independent native quarantine/placement and VMware network mapping remain required |
| Real local Terraform experiment | Built-in data resource proves saved-plan use, stale-plan rejection, output capture and private artifact permissions | No platform provider, remote backend or infrastructure is exercised |
| Repository release settings | Reviewable required-check/review ruleset and administrator procedure | Settings are not enabled by committing the file; independent reviewer coverage is still needed |

Terraform defaults remain prepared/restricted. The OpenStack-first increment
below adds explicitly reviewed power/connectivity transitions. Full adopted
guest hardening, native drift repair, upgrades and coordinated retirement remain
unfinished. W01–W29 remain open under their actual acceptance criteria.

## Reference service and qualification increment

The [reference decisions](reference-realization.md) choose the internal IPv4
OpenStack fixture as the first qualification path, followed by the other two
required stacks. Product choices now have executable integrations:

| Delivered capability | Concrete behavior | Remaining boundary |
| --- | --- | --- |
| GitLab state configuration | Stable scope-derived HTTP state name and exact lock endpoints | Provision actual service/projects, verify access separation, locking and independent state recovery |
| [NetBox IPAM](netbox-ipam.md) | Reserve/confirm/deprecate exact tenant/VRF/prefix addresses; server ETags, ownership checks, persisted lost-write holds and read-only reconciliation | Actual NetBox 4.7 permissions/concurrency; compute-capacity reservations remain separate |
| [Confirmed IPAM to DNS](netbox-dns.md) | Initial A/PTR registration through the existing TSIG writer, exact confirmed receipt/current native readback, shared allocation lock and durable per-zone attempt; read-only recovery after lost responses or write-window expiry | Actual service permissions/durability, forward/reverse and resolver/secondary acceptance, IPv6 IPAM, coordinated retirement and external handoff records remain open |
| [DNS withdrawal before IPAM retirement](netbox-dns-retirement.md) | Exact original A/PTR generation withdrawal, retained markers, one durable attempt and read-only recovery; NetBox deprecation requires current matching tombstone receipts for every managed DNS slot | External exposure/dependency cleanup, native writer exclusion, service qualification, retention and name/address reuse remain separate gates |
| [Ubuntu guest services](guest-services.md) | Scoped SSH CA principals/revocation, separate recovery key, explicit resolver, persistent bounded journal and authenticated TLS logging | Trusted images, full selected hardening profile, actual collector receipts, certificate issuance/renewal and native convergence |
| [Backup enrollment and restore](restic-recovery.md) | Confined systemd schedules, disable/withdraw, encrypted file capture and isolated byte-verified restore with separate authority | Server-side append-only/retention, independently recoverable keys and application consistency/acceptance |
| [Edge activation](edge-activation.md) | Exact IPv4 service tuples, atomic scoped nftables table, bootstrap/active/withdraw, kernel lease expiry and established-session withdrawal | Native attachments, same-subnet isolation, route ownership, HA/reboot fail-closed behavior and capacity |
| [Target campaign collector](target-qualification.md) | Native API readback before/after pinned certificate-SSH probes, exact TLS health bytes and healthy controls around denial cases | Execution on actual installed tuples and independent acceptance of the complete campaign |

These are small, separately reviewable commits in PR #46. They do not install a
live service or populate accepted site/platform/assurance indexes. Executable
operations require private actual inputs; documentation examples never supply
native authority.

## OpenStack commissioning implementation

The [bootstrap runbook](openstack-bootstrap.md) now connects existing prepared
resources to the guest/service and qualification tools. Small PR commits add:

| Capability | Implemented behavior | Native boundary |
| --- | --- | --- |
| Terraform lifecycle | Explicit prepared/bootstrap network, router, port and VM state; exact /32 service rules; config-drive prerequisite; data-preserving withdrawal | Existing images and actual edge/service paths must be accepted before powering guests |
| Saved-plan transition | Prior successful scope outputs and native IDs, exact input hash, expiring acceptance references; no unrelated mutation, replacement or deletion; revalidation before apply | External change custody and native writer exclusion remain operator responsibilities |
| Nova/Cinder/Glance readback | Two stable GETs, exact compute hosts, encrypted retained volumes, matching attachments and protected image hashes | Actual installed API versions and privileged read access are required; API equality does not prove isolation or HA |
| Campaign v2 | Network plus workload observations before/after guest traffic; all guest-output server/volume IDs and boot-image lineage must be covered | Execute on the commissioned site and independently accept complete security/recovery results |

Follow the [site commissioning sequence](site-commissioning.md) to run these tools
on actual infrastructure. The VMware/Nutanix increment below adds restricted
controls without completing those stacks. Native fencing, automatic drift
containment, upgrades and coordinated retirement remain separate implementation
work. Accepted site/platform indexes remain empty.

## VMware and Nutanix lifecycle implementation

Further small commits in PR #46 implement the [platform lifecycle contract](platform-lifecycle.md):

| Capability | Implemented behavior | Remaining native boundary |
| --- | --- | --- |
| AHV power/NIC lifecycle | Prepared OFF/disconnected defaults, explicitly accepted ON/connected bootstrap, data-preserving return to prepared | Effective Flow enforcement, image initialization and actual placement/storage/guest acceptance |
| NSX domain lifecycle | Sorted exact IPv4 TCP/UDP service exceptions, mandatory dual-family drop, connected segment; withdrawal removes exceptions and disconnects | Effective DFW precedence/membership/exclusions, same-host enforcement and accepted upstream service paths; vSphere power remains computed |
| Exact lifecycle plan review | Prior native identity and immutable non-lifecycle inputs, expiring references, restricted update fields; unknown security values, drift and replacements block | Issuing authority, cross-writer exclusion and actual native reconciliation |
| AHV VM snapshots | Exact native tenant, host/cluster/project/category, power, CPU/memory, NIC and retained-disk expectations with strong ETags and stable GETs | Selected fields only; no VM task completion, Flow enforcement, HA or application recovery claim |
| Campaign v3 | AHV snapshots plus network readback before/after guest probes; every workload VM and NIC subnet/address bound to the campaign | Execute on actual installed APIs and independently accept complete results |

The lifecycle revision `c0e4334` passed
[architecture/automation CI](https://github.com/awalker0878/multi-tenant/actions/runs/35515987373)
and the [routed-family campaign](https://github.com/awalker0878/multi-tenant/actions/runs/35515987368).
The VM snapshot revision `8a27774` passed
[architecture/automation CI](https://github.com/awalker0878/multi-tenant/actions/runs/35516459827)
and the [routed-family campaign](https://github.com/awalker0878/multi-tenant/actions/runs/35516459833).
Campaign-v3 revision `12436e8` passed
[architecture/automation CI](https://github.com/awalker0878/multi-tenant/actions/runs/35516700256)
and the [routed-family campaign](https://github.com/awalker0878/multi-tenant/actions/runs/35516700258),
plus 1,490 local Python/source tests and 80 route/model checks. Subsequent
revisions need their own exact PR checks.
These are synthetic API/provider tests and disposable local experiments; no
actual VMware or Nutanix site was contacted or qualified.

## Flow service and vSphere reconciliation increment

Further small commits in PR #46 add concrete integration without issuing native
acceptance:

| Capability | Implemented behavior | Remaining boundary |
| --- | --- | --- |
| Flow service lifecycle | Exact IPv4 peer/TCP-or-UDP port exceptions in the existing owned policy; withdrawal removes exceptions; both deny rules, category, VPC, ENFORCE and logging retained | Installed policy semantics/precedence, native task outcomes and live allowed/denied/withdrawal behavior |
| Flow saved-plan contract | Prior policy/category/VPC IDs, exact service intent, immutable deny pair; unbound bootstrap, extra selectors, unknown security values and unrelated updates block | Separately accepted authority and native writer fencing |
| Flow readback and campaign v4 | Strong-ETag policy snapshots plus AHV/network observations; every domain policy bound to output IDs and VM category/NIC VPC membership before/after traffic | Effective enforcement outside the selected policy set, actual task coverage and site qualification |
| vSphere VM readback | Exact MoID/BIOS UUID/instance UUID, config revision, full device backings, host/resource-pool placement and power; repeat GETs hold observed concurrent change | Installed VI JSON 8.0.3.0 schema, native ownership/mapping and complete security/storage/HA acceptance |
| vSphere task evidence | Accepted exact task/VM/operation/queue-time/event-chain binding, success chronology, pending/failure/unknown holds and terminal-regression checks | Complete composite task coverage, native writer fencing and operation-wide ledger reconciliation; no replay/repair authorization |
| VMware campaign v5 | NSX plus vSphere snapshot or task evidence around certificate-SSH traffic, separate origins/trust/credentials and combined report hashes | Independent NSX/vCenter mapping, effective DFW membership, site commissioning and live HA/security/recovery |

Local verification passed 1,523 Python/source tests with no skips and 80 route/model
checks. Flow/provider and vSphere HTTPS fixtures remain synthetic; current hosted
CI supplies the pinned provider/Ansible/disposable-lab gates for the exact PR head.
No live infrastructure was contacted or changed. The remaining vSphere power and
guest-bootstrap writer, composite lifecycle reconciliation, actual site services
and native acceptance work remain open. See the
[updated commissioning runbook](site-commissioning.md).

## vSphere task-tree and held-attempt recovery increment

Small commits in PR #46 extend the existing observers and executor evidence:

| Capability | Implemented behavior | Remaining boundary |
| --- | --- | --- |
| Task witnesses | Offline review recomputes exact task outcomes and chronology from selected native fields; fault/result text is excluded | Accepted operation/task mapping and authentic native evidence remain external |
| Bounded task trees | Exact ancestry and child-history sets checked before/after VM reads; filtered session collectors are paginated and destroyed; missing/extra/pending/failed children hold | Installed history visibility/retention, clone/result-bearing and cross-entity workflows, future or unrelated work and actual native fencing |
| Held Terraform attempt review | Known existing VM updates bound to exact saved-plan bytes, sealed scope/origin, immutable attempt and current ledger head; separate private packet preserves the hold | Unknown creates/replacements/deletes need ownership reconciliation; no adoption, replay or ledger release is supplied |
| Recovery control chronology | Fencing and quarantine observations must precede readback; later controls require a fresh report | Genuine native exclusion and containment must be established through their owners |

Local verification passed 1,544 Python/source tests with no skips and 80
route/model checks. HTTPS/history and attempt-ledger fixtures remain synthetic.
The implementation revision `799ab90` passed
[architecture/automation CI](https://github.com/awalker0878/multi-tenant/actions/runs/35520842368)
and the [routed-family campaign](https://github.com/awalker0878/multi-tenant/actions/runs/35520842351).
Subsequent revisions require their own exact PR checks.
No live infrastructure was contacted or changed, and no native acceptance index
was populated. The fenced power/guest-bootstrap owner, full operation-wide native
reconciliation, actual commissioning and live HA/security/recovery remain open.
See [vSphere readback](vsphere-readback.md) and
[held-attempt recovery](terraform-recovery.md) for the supported limits.

## Template-clone evidence and planned-configuration increment

Further small commits extend native reconciliation without issuing a clone,
power change, state adoption or ledger release:

| Capability | Implemented behavior | Remaining boundary |
| --- | --- | --- |
| Clone result witness | Exact accepted source entity and returned destination VM; missing, foreign or contradictory results hold | Native operation description/TaskInfo shape and original execution trail require installed-tuple acceptance |
| Template clone tree | Source BIOS/instance UUID, template flag and revision sampled around destination/task/history reads; source/result witnesses recomputed offline and usable in campaign v5 | Source image provenance, submission-time immutability, unsupported internal/cross-entity tasks and complete operation-wide coverage |
| Planned configuration binding | Existing VM name, CPU, memory, topology and pool compared with native expectations and sealed inputs; unsupported updates, drift, moved/imported addresses and unknown values hold | New clone ownership/state reconciliation and the unchanged disk/NIC/security baseline remain separately required |

Local verification passed 1,556 Python/source tests with no skips and 80
route/model checks. Implementation revision `39f0ea1` passed
[architecture/automation CI](https://github.com/awalker0878/multi-tenant/actions/runs/35521927155)
and the [routed-family campaign](https://github.com/awalker0878/multi-tenant/actions/runs/35521927158).
Later revisions require their own exact PR checks. These are synthetic API and
private-ledger fixtures and disposable engine/lab experiments. Native writer
exclusion, fenced power/guest-bootstrap control, state adoption/authorized ledger
recovery, actual commissioning and live HA/security/recovery remain open.
No actual site was contacted or changed. The commissioning runbook now records
the clone-specific native failure scenarios and evidence to collect.

## Existing-VM activity reconciliation increment

Small commits in PR #46 address the gap between a matching accepted task tree and
separate visible operations on those same VMs:

| Capability | Implemented behavior | Remaining boundary |
| --- | --- | --- |
| Scoped VM activity collection | Exact VM/`self` collectors read all pending work and work completed since the attempt; older queued work is not excluded; bounded paging and collector cleanup | Installed filter behavior, RBAC visibility and history retention require native qualification |
| Activity reconciliation | Before/after activity must equal the accepted full task set and direct witnesses; additional/omitted tasks, transitions, contradictory chronology and changed evidence hold; offline review recomputes witnesses | Synchronous/no-task operations, other entities, hidden/expired tasks and future work remain outside this coverage |
| Held-attempt requirement | Receipt review requires this profile and binds its window to the immutable attempt start; an older known-task-only profile or shifted window is refused | Original ledger remains held; native fencing, state adoption and authorized forward recovery remain external |

Local verification passed 1,571 Python/source tests with no skips and 80 route/model
checks. HTTPS task-history and private-ledger fixtures remain synthetic.
Implementation revision `1644abc` passed
[architecture/automation CI](https://github.com/awalker0878/multi-tenant/actions/runs/35523032734)
and the [routed-family campaign](https://github.com/awalker0878/multi-tenant/actions/runs/35523032789).
Later revisions require their own exact PR checks; these do not qualify an actual
site. The [readback](vsphere-readback.md),
[recovery](terraform-recovery.md) and [commissioning](site-commissioning.md) runbooks
document the profile and additional native cases to exercise.

No live infrastructure was contacted or changed. Fenced vSphere power/lifecycle
control, complete operation-wide native reconciliation, actual commissioning and
live HA/security/recovery qualification remain open.

## VMware network association increment

Small commits in PR #46 implement the selected cross-owner association described
in the VMware build design:

| Capability | Implemented behavior | Remaining boundary |
| --- | --- | --- |
| vCenter portgroup reader | Exact NSX-backed ephemeral portgroup identity/revision, parent DVS identity and logical-switch UUID; repeated GETs and stable rounds | Installed response shape, per-port attachment and other backing types require independent evidence |
| NSX realized-switch reader | Segment-scoped realized entity reads bracket existing policy/config/status reads; missing, duplicate, incomplete, foreign or changing switch results hold | Native RBAC visibility, installed omission/entity semantics and effective DFW enforcement remain unqualified |
| Campaign v6 | Hash-bound domain outputs and workload inputs connect every owned VM NIC to its assigned portgroup and that domain's realized NSX switch; five readback reports per phase around traffic | Configured association is not atomic cross-system state, data-plane membership, guest IP identity, fencing or acceptance |

Local verification passed 1,587 Python/source tests with no skips and 80 route/model
checks. Implementation revision `aef0390` passed
[architecture/automation CI](https://github.com/awalker0878/multi-tenant/actions/runs/35523975850)
and the [routed-family campaign](https://github.com/awalker0878/multi-tenant/actions/runs/35523975856).
Later revisions require their own exact PR checks. New fixtures exercise real
dual-origin HTTPS child readers, private asset binding and mid-collection changes;
the new campaign test substitutes its guest probe and does not claim live traffic
or native isolation evidence.

The [network association runbook](vmware-network-binding.md) records exact inputs,
interfaces, unsupported realizations and remaining native acceptance work.
No actual site was contacted or changed. Fenced power/lifecycle control, complete
native reconciliation, actual commissioning and live HA/security/recovery remain
open; no acceptance index was populated.

## VMware port attachment increment

Two implementation commits in PR #46 extend the configured association checks
with bounded native port readback and campaign v7:

| Capability | Implemented behavior | Remaining boundary |
| --- | --- | --- |
| Exact port reader | Fixed `FetchDVPorts` reads for accepted switch/port keys bracket portgroup reads; complete unique result set, selected revisions, occupant, host, cookie and runtime checks | Installed VI JSON response/omission behavior and scoped visibility require commissioning; selected fields do not establish effective port policy |
| Campaign v7 | Each owned VM NIC must match one observed port's VM/NIC, host, MAC and connection cookie, in addition to v6's member/domain/NSX binding | Observations are bounded and non-atomic; DFW enforcement, guest IP identity, HA and writer exclusion remain separate |

Local verification passed 1,600 Python/source tests without skips and 80 route/model
checks. Implementation revision `e8cf3a4` passed
[architecture/automation CI](https://github.com/awalker0878/multi-tenant/actions/runs/35536985826)
and the [routed-family campaign](https://github.com/awalker0878/multi-tenant/actions/runs/35536985812).
Later revisions require their own exact PR checks. Tests cover fixed TLS requests,
missing/extra/duplicate rows, reused cookies, foreign occupants, host/runtime
changes, old-profile rejection and attachment changes after VM observation.
The campaign fixture uses real native-reader child processes but substitutes its
guest probe; it is not live native evidence.

The [network association runbook](vmware-network-binding.md) and
[commissioning sequence](site-commissioning.md) describe the required private
expectations and actual native acceptance cases. No actual site was contacted or
changed. Fenced vSphere power/lifecycle control, complete native reconciliation,
actual commissioning and live HA/security/recovery qualification remain open.

## VMware clone activity increment

The clone activity profile extends selected source/result/tree observations with
visible activity on the exact union of source and destination VMs. Shared
templates are queried once; each destination query remains mandatory. Pending
work has no time cutoff, and completion queries begin at the accepted attempt
start. Separate roots, old pending work, late completions, missing queries and
contradictory source/result witnesses hold.

Offline triage binds the window to the attempted operation and recomputes the
activity witnesses. Campaigns v5/v6/v7 support the profile without new assets;
v7 retains destination port/domain bindings. The existing-VM Terraform reviewer
explicitly refuses clone activity as a substitute for creation/state adoption
and preserves the ledger. Matching activity supplies no writer fence or authority.

Local verification passed 1,617 Python/source tests without skips and 80 route/model
checks. New tests exercise real TLS collector requests and cleanup, unreadable or
omitted source activity, shared templates, source/result mismatches, pending/failed
destination work, offline witness tampering, fencing/quarantine holds and the
full campaign child-reader sequence. The campaign fixture substitutes its guest
probe; these are synthetic checks, not installed platform qualification. Use the
exact published revision's PR checks for hosted engine results.

The [readback](vsphere-readback.md), [recovery](terraform-recovery.md) and
[commissioning](site-commissioning.md) runbooks record the new profile and required
native source/destination cases. No actual site was contacted or changed. Fenced
power/lifecycle control, complete native reconciliation, creation/state adoption,
actual commissioning and live HA/security/recovery qualification remain open.

### Recorded verification

The OpenStack lifecycle/readback revision `c11b09a` passed
[architecture/automation CI](https://github.com/awalker0878/multi-tenant/actions/runs/35514866135)
and the [routed-family campaign](https://github.com/awalker0878/multi-tenant/actions/runs/35514865933).
Local verification passed 1,474 Python/source tests and 80 route/model checks.
New HTTPS tests use disposable synthetic API fixtures; Terraform lifecycle tests
use provider mocks and the executor's synthetic plan boundary. No live Nova,
Cinder, Glance or Neutron environment was contacted. Subsequent documentation
changes retain their own exact PR checks.

At `15a574d`, [architecture/automation CI](https://github.com/awalker0878/multi-tenant/actions/runs/35490547048) and the [routed-family campaign](https://github.com/awalker0878/multi-tenant/actions/runs/35490547095) passed. This includes all 16 registered Terraform module/composition/root pairs, real Ansible syntax and local rejection/idempotence checks, and the two disposable packet families. Local Python verification at `9a76d90` passed 1,392 tests and 80 route/model checks; `15a574d` adds the tested ambiguous-input rejection case. Later revisions must use their own exact CI results; these links are not evidence for untested source.

The service/edge revision `0564e8b` passed [architecture/automation CI](https://github.com/awalker0878/multi-tenant/actions/runs/35512064544) and the [routed-family campaign](https://github.com/awalker0878/multi-tenant/actions/runs/35512064540). Its installed engines verified SSH/rsyslog/systemd configuration, real encrypted file recovery and actual nftables packet activation, withdrawal and expiry. The later target-collector and documentation commits require their own exact PR checks; previous passing revisions are not substituted for those checks.

The authoring runtime could not start Terraform provider Unix sockets; GitHub's Terraform engine job supplies the engine evidence. Native Linux convergence/idempotence, platform installation, real remote-state locking, guest bootstrap, actual service enrollment, native failure/restore and retirement have **not** been run. Earlier failed CI runs remain failed records; fixes were committed rather than disabling their gates. Local restic recovery and disposable namespace/SSH experiments are explicitly separate from these native obligations.

## AHV recorded-task reconciliation increment

The optional [AHV VM/task profile](nutanix-vm-task-readback.md) composes selected
VMM VM snapshots with a bounded recorded Prism task graph. It reads only accepted
IDs, brackets VM reads with all recorded tasks and requires stable complete
witnesses. Matching VM state cannot mask pending/failed/missing children,
incomplete entity coverage or terminal regression. The snapshot-only profile
retains its explicit lack of task completion evidence.

Offline recovery review recomputes witnesses and completion flags and binds the
creation interval to the attempted change. Campaigns v3/v4 use the exact bound
profile and preserve workload/network/Flow ownership and combined report hashes.
Writer-fence, quarantine, incident and generation holds remain in force. This
known-task profile supplies neither AHV Terraform plan/ledger integration nor
native fencing; the following increment adds a separate activity-based review.

Local verification passed 1,680 Python/source tests without skips and 80 route/model
checks. New tests use real loopback TLS and CLI/campaign child readers with scripted
task responses, including pending/failure, missing/foreign entities, truncation,
VM drift, terminal regression and offline evidence tampering. They do not run
native operations or guest traffic. Use the final published revision's PR checks
for hosted engine results. Installed compatibility, complete native reconciliation,
fenced power/lifecycle control and live HA/security/recovery remain open.

## AHV visible activity and held lifecycle review increment

The [AHV activity profile](nutanix-vm-activity-readback.md) adds fixed per-VM
Prism task queries before and after the recorded graph/VM sample. Pending work
has no age cutoff; terminal work is included from the attempted change. Bounded
complete pages, constant totals, ordering, full affected entities and agreement
with direct task GETs are required. Extra or changing activity holds. Offline
recovery and campaigns v3/v4 recompute and bind this additional evidence without
downgrading the workload profile or changing ownership/network/Flow checks.

The [held-attempt reviewer](terraform-recovery.md) now also binds existing AHV
power/NIC lifecycle evidence to the sealed transition, member inputs, saved plan
and immutable durable attempt. It checks selected CPU/memory/placement, exact
NIC identities/addresses and retained disk identities/slots/sizes/containers.
Unsupported changes, unknown values and partial coverage hold. Historical
transition validity is evaluated at the original attempt time; current apply
authority remains time limited. Every result leaves the ledger held and grants
no mutation, activation, replay or state-adoption authority.

Local verification passed 1,707 Python/source tests without skips and 80 route/model
checks. Added scripted TLS/CLI cases cover old pending and late-completed work,
page/count/filter contradictions, shared tasks, direct/list disagreement,
offline witness tampering, actual campaign child readers, altered plans and
sealed artifacts, historical expiration, concurrent review and ledger preservation.
Use the final published revision's PR checks for hosted engine results. Exact
installed query semantics/RBAC visibility, real cross-writer fencing, complete
native reconciliation, site commissioning and live HA/security/recovery remain
unqualified. No live infrastructure or native acceptance index was changed.

## vSphere device and attachment recovery increment

The [held-attempt reviewer](terraform-recovery.md) now binds retained disk
keys/UUIDs, VMDK paths, capacity, datastore and SCSI layout to the saved plan and
sealed member inputs. It requires the current module's explicit persistent,
thin, unshared boot/optional-data layout and retained-file settings. Planned
NIC key/MAC/adapter/network identity must match; CPU/memory/topology remain the
only permitted updates. Unsupported layouts and device changes remain held.

Fresh [native port-attachment evidence](vmware-network-binding.md) is now required
for vSphere receipt review. It resolves the planned network MoID through observed
switch/portgroup keys and checks exact VM/NIC occupant, port cookie, host and MAC.
Shared portgroups require complete distinct owned attachments. Both VM and network
reports must be collected after current fence/quarantine verification; every
outcome retains the durable ledger hold.

Portgroup/port reports now retain selected before/after witnesses for offline
recomputation. VM/task review checks both selected VM snapshot hashes against the
accepted baseline and preserves a runtime-question indicator without exporting
question text or unselected device/guest values. Rehashed summaries cannot hide
contradictory witnesses; older reports without these fields must be recollected.

Local verification passed 1,734 Python/source tests without skips and 80 route/model
checks. Added tests cover foreign/missing/unknown disks, exact optional-data slots,
native network MoID/key distinction, NIC/port/cookie/host substitution, shared
groups, stale or pre-fence network evidence, offline witness tampering, private
CLI output and ledger preservation. Hosted engine results belong to the final
published revision's PR checks. Synthetic fixtures do not qualify real native
response/default semantics, storage compliance, fencing or site behavior.
Fenced vSphere power, full native reconciliation/adoption, actual commissioning
and live HA/security/application recovery remain open. No live infrastructure
or native acceptance index was changed.

## Flow policy activity and held lifecycle review increment

The explicit [Flow activity profile](nutanix-flow-activity-readback.md) adds recorded
Prism tasks and bounded per-policy queries around strong-ETag snapshots. It reuses
the tested entity-activity checks: all pending work, terminal work completed since
the original attempt, complete bounded pages/counts, exact affected policies and
agreement with direct task GETs. Extra, omitted, changed, pending or failed work
holds. Campaign v4 selects the bound Flow profile without downgrading and retains
all network/AHV/domain/category/VPC ownership and combined report-hash bindings.

Both Flow readers now retain policy/ETag hashes and a full native-shape verdict.
Offline review checks these alongside task/activity witnesses; contradictory
summaries cannot hide a native selector omitted from the expected projection.
Reports without the new witnesses must be recollected. Consistency checks do not
authenticate a collector or prove effective enforcement.

The [held-attempt reviewer](terraform-recovery.md) now binds existing Nutanix domain
service bootstrap/withdrawal to the sealed transition, inputs, saved plan and
immutable attempt. It requires exact policy/category/VPC/name/service intent and
retained deny IDs. Only explicitly computed new service-rule IDs may be unknown;
unrelated domain resources must be resolved no-ops. Unknown policy identities,
security fields, adoption, replacements, deletes and partial coverage hold.
Historical transition validity does not renew current apply authority. Every
review preserves all ledger bytes and grants no mutation or activation authority.

Local verification passed 1,763 Python/source tests without skips and 80 route/model
checks. Repository/documentation checks passed with 11,062 active links and no
issues. New scripted TLS/CLI tests cover task failures/pending/extra activity,
policy shape and ETag contradictions, offline witness tampering, actual campaign
child dispatch, sealed artifacts, retained/generated rule IDs, sorted service
insertions, historical validity and ledger preservation. Hosted engine results
belong to the final published revision's PR checks; fixtures are not native acceptance.

Installed API/query/RBAC/retention, actual provider default/rule-ID behavior,
policy enforcement/precedence and cross-writer fencing remain unqualified.
Fenced vSphere control, operation-wide native reconciliation/adoption, actual site
commissioning and live HA/security/application recovery remain open. No live
infrastructure or native acceptance index was changed.

## Package disposition and next concrete work

“Partial” credits delivered code or retained functionality, not operational acceptance. “Blocked” identifies missing target/product/authority inputs required for meaningful implementation or execution. Proposed accountable roles remain in the backlog; no individuals or approvals have been invented.

| Package | Current disposition | Work still required to meet acceptance |
| --- | --- | --- |
| W01 | Partial | Replace symbolic environment/cluster examples with actual supported site/cell/platform/API/hardware/licence tuples, image/service offers, owners and first qualification target. Confirm physical mappings and co-residency policy. |
| W02 | Blocked on runner/trust services | Build the selected recoverable native runner, private stores, artifact trust, credential injection/rotation and independent name/time/identity recovery. CI pins alone do not supply P0. |
| W03 | Partial GitLab integration | Scope-specific backend/lock configuration is implemented. Provision the actual GitLab projects, enforce access separation/encryption/versioning, and demonstrate concurrency and independent state restore. |
| W04 | Partial | Core-pinned Linux SSH inventory/profile and guard tests exist. Build the selected execution image, scoped credentials and privileges; prove native convergence/check mode and implement Windows/other offered connection profiles. |
| W05 | Blocked on hardware/fabric selection | Implement actual OOB, firmware, port/underlay/VLAN/VNI/VRF/MTU/HA attachment operations using the selected supported device interfaces; qualify failure and configuration recovery. |
| W06 | Blocked on installed tuples/installers | Select supported Nutanix, VMware/NSX and OpenStack installer/adoption tracks; implement their real inputs, observed readiness and interrupted-install reconciliation. No generic installer stub substitutes for this. |
| W07 | Blocked on service/storage selections | Commission images/templates, entitled pools, storage classes, resolver/time, artifacts, telemetry, identity/PKI and protection consumers; verify bootstrap-to-steady-state transfer. |
| W08 | Partial Linux edge realization | Scoped nftables rules, leases and withdrawal are implemented and locally packet-tested. Commission native ZIP/edge attachments, routing, administrative separation, boot/HA containment and surviving capacity. |
| W09 | Partial placement checks only | Implement actual tenant project/RBAC/quota/pool/AZ entitlement mutations and delegated-credential negative tests. Declared eligibility is not enforced native entitlement. |
| W10 | Partial NetBox IPAM integration | Native API reserve/confirm/retire and uncertain-outcome reconciliation exist. Qualify the actual service, integrate its receipts with accepted records and implement separate compute-capacity hold/renew/release. Address reuse remains held pending cleanup. |
| W11 | Partial NetBox-to-DNS integration | Initial A/PTR registration and exact owned withdrawal bind confirmed IPv4 receipts, original generations and current native readback; durable attempts and read-only recovery hold uncertainty. Integrate accepted external IPAM/reservation records and IPv6; qualify actual services, forward/reverse and propagation, conflicts, uncertainty and reuse. |
| W12 | Partial | Compositions, source-bound execution, receipt handoffs and exact OpenStack/NSX/AHV/Flow lifecycle controls exist. Complete remaining vSphere/native lifecycle, integrate accepted edge routes/attachments, capacity and IPAM; qualify whole fixtures and partial effects on all three stacks. |
| W13 | Partial Linux configuration | Hostname/time/kernel, SSH certificates, resolver, bounded logging and the OpenStack config-drive bootstrap prerequisite exist. Deliver actual trusted images, full adopted hardening, patch/reboot/resume and other offered OS profiles; run native convergence. |
| W14 | Partial selected service enrollment | SSH CA/principals/revocation, TLS log transport and restic schedule/withdrawal exist. Integrate actual issuing/KMS, monitoring, collector acceptance, package and storage services; exercise renewal/revocation and independent restore. |
| W15 | Partial expiring activation | Scoped edge bootstrap/active/withdraw policy and established-session withdrawal are implemented. Connect accepted native attachments, route/reply paths and full readiness authority; qualify boot/HA behavior. Terraform defaults remain restricted. |
| W16 | Partial workload readback | OpenStack observations are bound in campaign v2; AHV snapshot, recorded VM/task graph or visible VM activity plus network evidence in v3/v4; explicit Flow snapshot or policy/task/activity evidence in v4; vSphere VM/task-tree/template-clone/activity and NSX evidence in v5; selected member-to-portgroup-to-segment associations in v6 and exact port occupants/cookies/host/runtime in v7. Qualify installed APIs, query/count semantics, history/activity, realized entities and port visibility; complete remaining task/entity/Flow coverage, effective DFW membership and unsupported network realizations. Do not infer task completion from snapshots or Terraform success. |
| W17 | Partial reconciliation evidence; native fencing blocked | Task/source/result witnesses, bounded AHV and Flow recorded-task/activity review, bounded vSphere child history, visible existing-VM and clone source/destination activity, and held-attempt plan bindings for supported vSphere configuration/devices/native port attachments, AHV power/NIC lifecycle and Flow domain service transitions are implemented. Deliver actual cross-writer fencing, full late/uncertain outcome reconciliation and authorized repair/adoption/cleanup. Review preserves all ledger holds. Serial Ansible and Terraform state locks do not fence native tasks. |
| W18 | Partial operator executor delivered | Plan/apply bundles, bounded native commands, durable uncertainty holds, receipt handoffs and held-attempt review packets are implemented. Integrate the chosen change/automation system with live preflight/reservation, authenticated approval custody, cross-writer fencing, native reconciliation and activation. Provision and recover the actual runner/ledger; no unattended native runner is installed. |
| W19 | Native implementation/qualification open | Decide offered address families. Compiler currently rejects non-IPv4 internal allocations. Deliver native IPv6/dual-stack modules, guest initialization, routes/policy/services and observations for each selected profile; local IPv6 labs are separate evidence. |
| W20 | Collector implemented; actual campaigns pending | Use the bound native/guest collector in restricted campaigns for all three exact installed tuples, complete HA/bypass/capacity tests and independently accept exposure/withdrawal evidence. All native indexes remain unqualified. |
| W21 | Operational integration open | Connect scheduled drift/health/capacity checks to selected observers and alerting, classify emergency/security/unknown drift, and exercise owned incident containment/release. Guest convergence is not a platform drift service. |
| W22 | Lifecycle implementation open | Add accepted resize/scale/growth, image refresh, patch/reboot, provider/platform/collection upgrades, rotation and replacement workflows with actual maintenance budgets and requalification rules. |
| W23 | Partial restic capture/restore | Encrypted scoped file capture, confined scheduling and isolated byte verification are implemented and locally exercised. Provision append-only protection, independent retention/keys, catalogues and application-consistent exports; measure native application RPO/RTO. |
| W24 | Blocked on accepted adoption/recovery design | Deliver exact native import/state mappings, same-service re-creation, supported portable data transitions, and any promised synchronization/cutover/failback with writer exclusion. No blind state move or cross-stack live migration is supplied. |
| W25 | Partial DNS/IPAM retirement; other authorities remain open | Exact owned A/PTR withdrawal retains tombstones; NetBox deprecation requires current matched cleanup of every managed DNS slot. Complete withdrawal and cleanup across policy/routes/enrollment/native resources, external DNS, retained-copy/key transfer and independent cleanup acceptance. Address/name release and reuse quarantine remain unimplemented. |
| W26 | Partial | Catalogue/provider checks, composition mocks, cluster/inventory negatives, Ansible guards and the real built-in Terraform saved-plan experiment exist. Add actual native operation campaigns, remote backend locking/recovery, service integrations and runtime tests as targets/interfaces are selected. |
| W27 | Maintained docs delivered; operational acceptance open | Current paths, commands, commits and limits are documented. Add actual as-built records, assigned maintaining owners/cadence, accepted operating MOPs and release evidence after qualification. |
| W28 | Conditional; no public profile selected | Select and implement ingress/WAF/LB, PAZ capacity, DNS/certificates, backend identity, HA/recovery and withdrawal; run its independent campaign. Internal OZ/RZ examples do not expose public service. |
| W29 | Conditional; extensions unselected | For each adopted assurance/bare-metal/container/accelerator/stretch/cross-stack/additional-platform offer, supply its design, real automation and separate native evidence/limits. |

## Inputs needed to unblock the integrated build

Provide accepted records through private operator systems, not repository commits containing secrets:

1. Actual first site and lifecycle target; three platform installed tuples and supported installer/adoption choices; native endpoints and scoped access; cluster/host/zone/failure-domain mappings and physical fabric/edge selection.
2. Actual instances/endpoints and custody for the selected GitLab, NetBox, DNS, SSH CA, TLS collector, restic and Linux edge profiles; independently recoverable automation/ledger/key storage; the remaining capacity, storage/image and package/monitoring services.
3. Declared image/OS/address-family/service/recovery offers, change and resource owners, restricted qualification authority, permitted bootstrap paths, and evidence locations.

The reference product choices are already recorded and implemented to the limits above. These private inputs identify real assets and remaining service boundaries; they cannot be inferred from symbolic documentation. Supplying them is not evidence that the work is complete: each package still needs actual execution results and its accepting authority.
