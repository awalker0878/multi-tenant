# Selected application migration runtime

The installed `provisioner.migration` package now composes the existing native
intent registry, cross-scope restic executor and VMware power/task owner for the
selected VMware → OpenStack Ubuntu 24.04 application rebuild/restore path. Its
repository implementation and synthetic fault tests do not qualify a native
route or complete B30–B37.

## Approval and descriptor binding

The canonical migration plan selects the complete private execution artifact
through `spec.execution.artifactDigest`. The artifact's `datasetSelectionDigest`
and `cutoverSelectionDigest` select the exact data and source-power descriptors.
These descriptor digests use the control application's compact
`canonical_record_digest` convention. Original restic capture/envelope digests
keep their existing encoded-byte convention.

Descriptors exclude the final plan and runtime transfer envelope. After the plan
is frozen, the transfer envelope includes that exact canonical plan, its digest,
and the live worker grant. This avoids a self-referential artifact/plan digest.
Changing a repository, source snapshot/receipt, dataset mapping, target root,
selected metadata, source VM request or resource limit requires a new approved
selection and plan. Neither an earlier comparison nor a packet boolean provides
execution authority.

`ApplicationDataSelection` verifies complete canonical dataset coverage, distinct
source receipts, non-overlapping roots, known useful byte counts and selected
POSIX owner/group/mode metadata. Each dataset preserves the original source
configuration, receipt and useful-file manifest. Cross-scope restore creates its
own destination receipt and does not relabel source evidence.

## Actual effects and retained outcomes

`ApplicationDataRunner.execute_dataset` checks the actual current worker grant,
owner epoch and independently commissioned resource binding, prepares a
`RESTORE_DATA` intent, durably records the child attempt and claims the central
intent once. It then calls the package-owned
`restic_transfer.execute_authorized_transfer`, including its per-command live
identity, approval, lease, source/destination and envelope checks.

Both new effect runners require the concrete `ApplicationCommandAuthority`,
which the installed activities supply. Its separate preclaim check performs
normal current admission without excluding any unresolved intent. After
the actual native intent claim, every repository command and VMware request
rechecks the full protected execution artifact, exact admitted job and current
qualification/operating controls under `PostgresExecutionAuthority`'s continuation
transaction. The transaction independently verifies the original typed worker
grant and excludes only its own current claimed intent from the uncertainty
gate. A selected qualification or operating acceptance withdrawn between
commands stops the next command. A new or uncertain sibling intent remains held.

A started child is never restored again automatically. Interruption, deadline,
revocation, invalid bytes/metadata and lost completion acknowledgement remain
held. `reconcile_dataset` accepts only the original protected envelope and
destination/restore receipts, rereads current useful bytes and metadata, and
issues no repository command. It requires the current original authority. A
changed owner/grant mapping needs the existing independent native registry
resolution path rather than rebinding this old envelope.

Each child has a separate journal and lock, permitting bounded independent child
activities. `join` rereads the retained child artifacts, requires every selected
mapping, recomputes each consistency-group join and verifies complete plan
coverage using the existing dataset acceptance owner. These joins verify file
bytes and selected metadata. They do not establish application consistency,
native intent resolution, isolation or production activation.

Successful local restore does not resolve the central native intent. Its result
explicitly requires independent observation and the existing exclusion/reviewer
path. A restore receipt cannot substitute for those controls.

## Enforced transfer bounds

The selected data runner requires `LinuxTransferResources`, supplied by the
enrolled worker rather than hydrated from a request. Before and after every
restic command, it verifies:

- The worker remains in its exact unified domain cgroup.
- The kernel I/O controller limits read/write bandwidth and block IOPS for the
  exact local staging block device.
- The target belongs to a dedicated staging mount whose physical filesystem
  ceiling does not exceed the approved staging byte budget, with `nosuid`,
  `nodev` and `noexec` enforced before restore.
- The captured useful bytes and manifest fit the currently available staging
  space before restore starts.

The actual restic command also receives `--limit-download`. An unlimited cgroup,
shared larger filesystem, changed device, insufficient space or escaped worker
is held before the effect. Resource creation and reservations remain B23 owner
responsibilities. Block IOPS limits are not limits on cached filesystem
operations. Measured elapsed time and useful byte counts are retained; they are
not native performance qualification.

The optional resource-control argument leaves ordinary backup's minimal package
closure unchanged. The selected migration runner always requires it. Special
files, links, arbitrary format conversion, extended ACL/xattr semantics and
application-native replication are not added to the supported path.

## Source shutdown and the write boundary

`SourceFenceRunner.source_fence` selects every original source VM by its exact
approved power request. It prepares/claims `SOURCE_FENCE` through the native
registry and invokes the existing durable VMware power/task owner. The concrete
transport rechecks the current source grant before and after each native
request. Completion and read-only resume both reread the native task, VM/device
state and activity; a retained shutdown receipt cannot hide a subsequent source
restart.

The shutdown-only owner retains `SOURCE_POWERED_OFF_RESTART_EXCLUSION_HELD`.
The separately enrolled `ApplicationLifecycleRunner` additionally stops/masks the
selected application, captures its final data under current authority, powers
and observes the source off, and removes its exact retained data disks through
a genuine vSphere task. Persistent disk exclusion and independent original
writer/readback proof are mandatory before final sync or source return. A power
receipt alone does not establish that exclusion.

Separate staging and cutover workflows require current handover accounting and
an explicit existing-target power phase before guest/data contact. Nova request
IDs are retained as request identities, not B11 task IDs. Isolated rehearsal,
final restore, application acceptance and target activation use the exact enrolled
systemd, repository, resource/service and independent readback owners. Missing
native enrollment holds each phase before its effect. Fixture success does not
prove native management reachability, traffic exposure or service acceptance.

`recovery_projection` still presents conservative read-only choices from the
original activation intent. The implemented pre-write source-return path requires
current source/target disk exclusions and independently observed no target writes.
The separately admitted post-write recovery owner retains actual target data and
performs fixed reattach, start, forward repair and activation phases with new
B10/B11 authority. It never restarts the old source and does not implement general
reverse-sync. Unknown original outcomes prohibit replay or resource release.

## Trusted Temporal composition

`ApplicationMigrationActivities` uses the actual
`PostgresExecutionAuthority`, a bounded no-follow protected descriptor store and
typed per-job worker runtime bindings. Only the immutable `AdmittedInput`, full
selected artifact digest, bounded member ID and explicit execute/observe mode
enter activity history. Full admission/selection checks run at loading,
immediately before the native owner and after the result. Worker secrets and
paths remain in runtime custody; retained result files expose only their digest
to Temporal.

Dataset inspection/join/reconciliation and activation recovery projection use
the separately named original-observation gate. This permits authorized retained
facts to be inspected while a new native admission is held. It supplies no
native credential and does not claim an effect or resolve uncertainty. Dataset
reconciliation still requires the actual original current worker binding before
reading useful files. Native VMware resume remains under its stricter actual
request authority.

## Selected guest, policy and service boundaries

`ObservedProvisioningRuntime.run_step` implements the fixed admitted delivery
owner interface. The installed service supplies the actual execution authority,
worker authority, native registry, tenant context, observed resource lease,
verified worker identity and exact grant/operation IDs. Requests cannot select a
module, callable, secret factory or native identity. It verifies the same approved
delivery/packet bindings before invoking an existing concrete owner.

| Selected stage | Implemented boundary |
|---|---|
| Terraform prepare | The existing saved-plan owner has typed current `DISCOVER_READ` hooks around each subprocess and grant-bounded deadlines. The concrete scoped planning credential owner authenticates the exact Keystone project/native origin before each subprocess; missing enrollment holds before dispatch. |
| Guest configuration | Validate the sealed bundle and require exactly one target whose native VM/operation equals the observed lease. Dispatch through the enrolled per-command server/connection owner with fresh authority and bounded credentials for each fixed remote command; hold if it is absent. |
| Local expiring edge policy | Require current `POLICY_APPLY` rather than a power grant, claim the original native intent and call the existing `nft_edge.apply`. Recheck the full execution artifact, real grant, exact binary and local guest identity around every kernel command. |
| Native/service campaign | Require OpenStack workload/native manifests to select the actual granted project, then call the existing campaign owner in-process. Recheck actual `DISCOVER_READ` before/after each observer and fixed SSH probe, and each direct OpenStack request. Return retained observations requiring independent acceptance. |

The local edge writer only supports the commissioned adopted OpenStack Ubuntu
24.04 VM itself. It rereads the guest's provider UUID, root execution, machine ID,
system namespace and each selected interface's primary connected IPv4 network.
Missing identity, remote controller execution, network drift, unnumbered or
secondary-address boundaries hold. This check does not prove broader routing,
HA, isolation or service acceptance. The native allow authority must expire
inside the actual worker grant window; the wrapper preserves the original
authority and receipt rather than widening them. A successful edge receipt is
not native intent resolution or production qualification.

`GuestCommandExclusion` has no permissive boolean/callback path. The concrete
`GuestCommandRuntime` and guarded Ansible SSH plugin recheck the original binding,
current grant, executable/input bytes, Unix peer and private connection custody
for each remote command. Multi-member work needs the exact current host grant for
each host. Checking only around an Ansible controller process is insufficient.
See [current command authority](../operations/current-command-authority.md).

The selected scoped planning owner separately uses a `DISCOVER_READ` grant,
fresh Vault credential and actual reader-role Keystone authentication for each
fixed Terraform planning subprocess. Creation's `VM_CREATE` context cannot
substitute for it. Missing commissioning retains
`SCOPED_PLANNING_CREDENTIAL_OWNER_UNAVAILABLE` as an enrollment hold.

Existing typed bootstrap dependencies, useful-service receipts, dataset coverage
and independent acceptance retain their original owners. Neither a campaign
summary nor a local policy/restore receipt auto-accepts DNS, identity, time,
trust, logging, monitoring, backup, activation or lifecycle operations.

## Activity contracts

Implemented activity names are:

| Activity | Current behavior |
|---|---|
| `application_transfer_dataset` | Actual claimed, bounded cross-scope restic restore; retain verified byte/metadata evidence or hold. |
| `application_reconcile_dataset` | Reread only the original retained transfer and current useful bytes; never rerestore. |
| `application_join_datasets` | Require complete exact group/plan coverage without promoting application acceptance. |
| `application_inspect_datasets` | Retain explicit unstarted/uncertain/completed child progress. |
| `application_source_fence` | Exact source application quiesce/final capture, native shutdown and retained data-disk removal; current independent original exclusion required. |
| `application_target_prepare` | Start the exact independently observed existing target with current Nova authority; retain its genuine request identity before further readback. |
| `application_rehearsal` | Fixed isolated systemd rehearsal and independent application/data acceptance; missing enrolled native owners hold. |
| `application_final_sync` | Bounded final capture restore and complete current source/database exclusions. |
| `application_cutover` | Current final consistency, counted service ownership and explicit target write admission/activation; independent final verification required. |
| `application_recovery_inspect` | Read the original tenant/job-bound activation intent and expose conservative recovery holds. |

`STAGE_VERIFIED` means one implemented stage retained its stated evidence. It is
not application migration completion. `HELD` includes a jobs-compatible reason
and a specific fixed hold code. The workflow must not automatically retry native
effect activities. Read-only reconciliation is explicit.

## Verification and remaining native work

`tests/test_application_migration.py` exercises real executor composition with
synthetic scoped authorities/engines, command bandwidth flags, kernel-control
readers, claim failure, acknowledgement loss, current byte/mode changes, grant
revocation, restart on resume, protected-store tampering and Temporal dataclass
serialization. Original restic and VMware power regressions continue to pass.
`tests/test_observed_provisioning.py` exercises the actual local policy owner,
operation separation, grant deadlines, revocation after a write, lost response
without repeat, local identity drift and mandatory remote-guest holds. Its
native subprocesses and local identity facts are synthetic fixtures.

The test engines and kernel fixtures are not native campaign evidence. Native
B30/B31 qualification still requires commissioned repositories/keys, dedicated
worker/cgroup/staging custody, actual metadata/consistency acceptance and measured
limits. B32–B35 native acceptance remains open for isolated rehearsal, persistent
writer fencing, final sync, traffic/write admission and useful pre/post-write
recovery; the implemented target power phase additionally needs a concrete
isolated management/bootstrap network owner before guest contact. B36
still requires administrator acceptance of complete portal/CLI actions. B37
native mutation remains held until minimum operating controls and independently
authorized site/application inputs are present.
