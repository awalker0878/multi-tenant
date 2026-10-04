# Current authority for planning and guest commands

The application worker enrolls concrete `WorkerCommandRuntime` owners against
the same current execution authority, B10 grant repository and mTLS verifier.
The transport evidence is the actual accepted `ssl.SSLSocket`. Forwarded peer
headers, queue JSON, credential files and serialized worker identities cannot
construct this runtime. An owner retains the original admitted job, selected
artifact, source commit, stage purpose, immutable parameters and physical input
digests; every command rechecks them. A changed peer trust context, revoked
grant or original approval, expired lease, replaced input, different stage or
changed package/source bytes holds before the next command.

After an actual B11 one-time claim, only that typed original intent can request
the root authority's continuation. There is no blanket exception for unknown
native work. A remote effect already dispatched can finish after revocation;
its intent remains uncertain until independent native observation and old
worker/credential exclusion prove the outcome. Cleanup cannot invent fresh
permission to continue the revoked operation.

## OpenStack read and planning enrollment

`provisioner.controlplane.worker.adapters.openstack_planning` owns the selected
OpenStack workload planning credentials. Its `ScopedOpenStackPlanningRuntime`
requires a separately enrolled `DISCOVER_READ` grant, one exact dynamic Vault
role, the existing `VaultOpenStackCredentialConsumer`, the reviewed nonsecret
cloud projection and a commissioned compute origin. The current implementation
requires the standard project `reader` role. It does not reuse a VM creation
grant, administrative role or operator-selected long-lived token.

Before each fixed Terraform `version`, `init`, `plan` and `show` command, the
owner rechecks current original authority, consumes a new one-use Vault wrapped
credential, and authenticates it against the actual Keystone v3 endpoint. The
token must belong to the original project and application credential, contain
only the selected reader role, and expose the exact compute origin, region and
interface. The fixed executable, arguments, output purpose, prepared source,
inputs, backend files and CA remain bound between commands. Each subprocess
uses a unique private ephemeral cloud file; the file and native secrets are
removed afterward. The existing reviewed contact and bundle formats remain the
historical audit record.

Commission the role against the selected cloud's actual service RBAC policy.
An authenticated role name alone does not prove that writes are denied. Retain
separate current read-allowed/write-denied campaigns, credential lease/revocation
evidence, backend namespace tests and native target qualification. Missing
enrollment produces `SCOPED_PLANNING_CREDENTIAL_OWNER_UNAVAILABLE`.

## Linux SSH and Ansible enrollment

`GuestCommandRuntime.execute_prepared` requires the concrete claimed original
`ObservedProvisioningGuard`, the exact observed VM binding, original private
approval file and prepared guest bundle. The owner retains a private process
listener and passes only its session location to the installed, source-bound
`hosting_guarded_ssh` connection plugin. The local protocol carries the
immutable original binding and command/input digests; it carries no credentials
or worker authority. Both client and server verify actual Unix peer UID, private
socket custody, bounds and replay protection.

The connection plugin checks every actual SSH invocation and retry before
contact and after the result. A machine ID check is part of the same remote
command. Native UUID behavior comes from the declared guest profile; application
phases additionally bind their selected source or target DMI UUID. The original
access target, host key, account, certificate, service assets, executable and
sealed package source are checked again by the retained controller. An old
mTLS connection cannot continue after verifier trust reload. The generated
inventory and connection configuration live in a private runtime directory;
the original sealed bundle is retained unchanged.

`GuestCommandRuntime.exchange` is for installed, source-owned application
callers constructing fixed command tuples. A lifecycle phase must first claim
its exact `LifecycleCommandGuard`. The shipped Python action bootstrap verifies
the independently selected deployed interpreter and source bytes before import.
Each root service or restic command remains a separate current-authority
exchange. No user-supplied shell text or subprocess exit status proves a guest
or service postcondition. Native output is retained privately and bounded.

Final target health and source return health use a separately enrolled
`NativeReadEnrollment` with the lifecycle's own immutable `VERIFY_READ` or
`SOURCE_VERIFY_READ` row. `ApplicationGuestReadAuthority` binds that original
read operation, VM, source bytes and job without preparing or claiming a B11
write. Its real worker subject and certificate must differ from the original
writer. Every contact checks current read permission through the root
observation gate and B10, including after an earlier native write is uncertain.
It can show only the selected production unit's fixed properties and run the
source-bound image or useful production health observation. It cannot run
service mutations, restic, filesystem actions or arbitrary Python.
The destination reader can also observe only the exact original initial
staging path under its immutable useful-byte ceiling before the separately
admitted cutover. A changed path, side or byte ceiling holds before contact.
After a separately approved forward repair, only the destination reader may
use the current same-target plan. It retains an actual immutable
`ApplicationRecoverySelection` and checks its original capture references,
current lifecycle digest and exact root plan purpose before every read. The
original source axis remains historical capture custody; it grants no source
read or rollback command through this exception.

The read command runtime additionally enrolls a `GuestReadCredentialProfile`
containing the trusted Ed25519 SSH CA, separate native reader principal and
source CIDR. Each contact consumes a fresh actual Vault
`hosting-application-ssh-read/1` projection, with exact fields `format`,
`grant_id`, `lifecycle_sha256`, `native_binding` (the binding key as a JSON
list), `machine_id`, `user`, `host_key`, `private_key` and `certificate`.
The certificate key ID is `hosting-read:<grant_id>:<job_id>:<lifecycle_sha256>`.
The owner verifies the actual signature, private/public key equality, single
reader principal, source-address critical option, no forwarding extensions,
short current lifetime, selected host and fresh certificate serial before SSH.
The reader account must differ from the actual original writer's enrolled SSH
account. Caller key/certificate files cannot replace this credential owner.
Fresh native secrets are staged privately and removed after the contact.
Commission the native account's forced read command profile and sudo rules
against the real guest; a scoped certificate alone does not prove native write
denial or current application health.

The actual Unix listener and pinned Ansible engine tests require a host allowing
AF_UNIX sockets. This execution container returns EPERM for socket creation;
those tests explicitly skip and require hosted execution. The actual worker
mTLS and command-between-revocation tests still execute through real loopback
TLS locally. Synthetic native transport and grant persistence in these tests
are not commissioned guest or PostgreSQL evidence.

## Selected Windows Server 2022 service enrollment

`provisioner.execution.windows_guest.WindowsGuestSelection` is a separate
immutable descriptor. `ScopedWindowsGuestRuntime` accepts only the
`windows_guest_apply` stage with `GUEST_CONFIG`, selection and canonical route
guest profile `windows-server-2022`, and one exact approved target machine
mapping. The packet has no parameters and exactly two files:
`windows_selection` and `winrm_ca`. It cannot borrow the Linux guest route.

The descriptor binds the observed native VM, logical target machine, HTTPS
`/wsman` listener, connect IP, SNI name, server leaf certificate and CA hashes,
Windows MachineGuid, native DMI UUID, mapped local account, exact client
certificate subject and UPN, PowerShell interpreter hash, and concrete existing
service names, executable hashes, image paths, exact dependency names, requested
state and startup mode.
It contains no PowerShell text, password, client key or reusable token.

Enroll a dynamic Vault role issuing the fixed
`hosting-winrm-dynamic-certificate/1` projection for the original grant and
descriptor. The role supplies a new short-lived client-only X509 certificate
and matching private key for every SOAP request. The certificate subject and
UPN must match the selected native certificate mapping, and its actual expiry
must fit inside both the native lease and current worker window. Configure the
Windows HTTPS listener and certificate mapping independently; qualify local
account/service ACL restrictions and revocation against the real image. The
owner uses certificate-only TLS, with no Basic, NTLM, agent or trust fallback.

The runtime claims the actual native intent before contact. Every shell Create,
fixed PowerShell Command, bounded Receive, Signal and Delete reacquires current
original authority and a fresh credential. It validates exact SOAP response
correlation, shell/command identity and bounded output. A fixed source-owned
script reads Windows Server build 20348, machine/native identity, mapped account
and actual interpreter bytes before any service action. Each service action
rechecks the exact existing service, binary and dependency set. Starting a service
requires every selected dependency already running, so it cannot implicitly
start an unselected sibling service. Stopping uses no force option. After mutation a separate fixed
service observation must match both requested state and startup mode.

`ScopedWindowsServiceReadRuntime` owns the independently enrolled
`windows_guest_observe` stage with `DISCOVER_READ`. Its real worker subject and
certificate differ from the original native writer, and the native mapped
account and certificate UPN are separate. The reader creates only the fixed
identity and existing-service observation commands. It consumes a fresh scoped
certificate before every SOAP request, rechecks the actual original B11 row
and retains its operation, request digest, worker and epoch references. It does
not claim a new native write or resolve the old intent. Its completion status
is `SERVICE_POSTCONDITIONS_VERIFIED_REQUIRES_NATIVE_EXCLUSION`, with
`native_quiesced`, `native_acceptance` and `production_activation` all false.
Observed SCM state and successful shell deletion cannot prove that the old
writer's command, shell or credential has been excluded.

After independent native recovery actually resolves the predecessor to
`EFFECT_PRESENT`, a separately selected `windows_guest_remediate` stage can
claim its own current `GUEST_CONFIG` intent. Before every request it checks the
same original VM, service, binary, desired policy and resolved predecessor.
An uncertain predecessor holds before claim or native contact. This bounded
remediation reapplies the selected existing-service policy; it does not install
boot drivers or repair firmware, disk, network or arbitrary guest code.

Both follow-up packets have exactly one parameter, `original_operation_id`,
and three files: `windows_selection` for the current enrolled descriptor,
`original_windows_selection` for the original writer descriptor and `winrm_ca`.
The original and current descriptors must select identical VM, listener, trust,
interpreter, services and desired policy; only the enrolled account and client
certificate subject/UPN may differ. The packet parser checks these immutable
inputs, portable dispatch refuses these enrolled-only stages, and completion
checks every actual guest identity, fixed observation and service postcondition
before publishing a marker.

The dedicated `windows-server-2022-existing-services/1` driver makes these
owners reachable through `SelectedWindowsExistingServices` on the existing
B09 queue. Its `EXISTING_GUEST_SERVICES` plan purpose binds one currently
observed VM in the same source and destination scope and snapshot, and preserves
its complete disk and NIC mappings. It is separate from mobility methods.
The protected `hosting-existing-windows-services-artifact/1` binds the current
source commit, workload revision, native scope and tuple, service commissioning
and operating evidence, exact fixed delivery stages and inline
`hosting-existing-windows-services-selection/1` descriptor. Its approved
`spec.windowsServices.selectionDigest` pins that inline descriptor; it selects
no creation, dataset, cutover or application lifecycle owner.

The fixed actions are `CONFIGURE_AND_OBSERVE`, `OBSERVE_ORIGINAL` and
`REMEDIATE_AND_OBSERVE`. A separately admitted follow-up retains only the old
admission/artifact/intent/request/lease/worker/epoch and descriptor references.
Before every request the actual root rereads original retained facts and the
actual B11 row; these references cannot hydrate old worker permission. Current
read and repair credentials remain separate new enrollments. Interrupted or
already executed activities require recovery rather than another native
invocation. Even a complete independently observed service state returns
`HELD` with `WINDOWS_SERVICE_NATIVE_EXCLUSION_REQUIRED`, and retains
`native_acceptance=false` and `production_activation=false`.

Results are `CONFIGURED_REQUIRES_NATIVE_ACCEPTANCE`; the B11 intent is not
resolved by this owner. Actual certificate-only TLS/SOAP tests cover revocation,
certificate and response replay, selected input changes and a successful
transport with wrong guest identity or failed service readback. They simulate
Windows command execution and native persistence. No Windows guest, real
PowerShell engine, dynamic certificate backend, boot remediation, data/application
lifecycle or directed migration has been commissioned here. These require
separate native evidence before Windows route registration or qualification.

The protocol follows Microsoft's MS-WSMV [remote shells][shells],
[commands][commands], [receive and completion][receive] and
[certificate mapping][mapping] specifications. The deployed listener must
qualify its concrete behavior, including certificate mapping and shell lifetime;
a client's timeout or successful shell deletion cannot prove old commands are
excluded.

[shells]: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-wsmv/593f3ed0-0c7a-4158-a4be-0b429b597e31
[commands]: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-wsmv/c793e333-c409-43c6-a2eb-6ae2489c7ef4
[receive]: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-wsmv/50cc2c38-e094-4d59-aec2-39e09f314862
[mapping]: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-wsmv/3da6ccd9-0cf2-4297-8225-461557bfb8d2
