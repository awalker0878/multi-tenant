# P07 native provisioning implementation

Scope: P07.01–P07.06; R07/R08/R16–R21/R25/R29–R31/R33.
The [delivery register](delivery-register.yaml) owns status and evidence;
[P07](phases/p07.md) and [G07](gates.md#g07--native-openstack-provisioning) retain
their native acceptance scope.

The first increment implements a local Lifecycle commissioning-input evaluator
and protected-record parser. The [runbook](../operations/runbooks/openstack-commissioning.md)
maps all fifteen required input groups to owners and Q05 cases. The checked-in
[record](../../release/p07-native-inputs.json) truthfully starts with no supplied
native facts. The evaluator returns a bounded, redacted missing-input report;
even a complete record grants no authority and establishes no native qualification.

The implementation rejects inconsistent unknown/observed states, duplicate or
omitted obligations, wildcard scope, changed packet/plan bindings, unbound evidence,
future/expired metadata and unreviewed/self-reviewed observations. Native-scope
and stop/revocation inputs cannot inherit E2 evidence. Parsing rejects duplicate
keys, nonfinite values, oversized files and final-component symlinks/nonregular
files, with value-free errors. That offline preparation adds no runtime dependency or HTTP surface.

The second increment adds saved-plan byte comparison and P05/commissioning binding
checks. It holds changed native tuples, artifacts, state lineage/serial/workspace,
toolchain records and ownership, missing/expired lock observations, changed
executors, non-independent observations and unresolved effects. Explicit version
and digest metadata are required for Terraform, providers, modules and the worker.
The comparison accepts only the initial isolated OpenStack provisioning contract;
retirement, operational execution and automatic replanning are outside this tool.
It does not verify the supplied records' authenticity, parse/apply the Terraform
binary, fetch dependencies or enforce native fencing. The future adapter must
obtain and verify actual owner/tool bytes under current authority. Full local
commissioning/preflight tests are part of the owned Lifecycle suite.

Actual installed tuples, interfaces and tooling remain runtime commissioning inputs
under ADR-015/016. Native infrastructure, allocation, guest/service adapters,
quarantine activation, native failure/restore/retirement and the reviewed native
support dossier were not delivered by those two preparation increments.
P06 continues to expose simulation only. A metadata checker is neither an OpenStack
adapter nor a substitute for the independent Q05/Q06 campaign.

## Native adapter component increment

The Lifecycle worker now supplies actual saved-plan subprocess and scoped
OpenStack readback adapters, an append-only PostgreSQL attempt journal and a
multi-workload Terraform module. The [native adapter runbook](../operations/runbooks/openstack-native-adapters.md)
records their exact supported boundaries and commands. Native inspection is
composed into an installed read-only command. The effect protocol is exercised
through its current-authority port, which still needs product native grant and
provider-side fencing integration before native dispatch can be enabled. This
increment supersedes the earlier statement that all adapter code is absent; it
does not complete native infrastructure execution, service enrollment, activation,
recovery/retirement or the Q05/Q06 dossier. Existing status and receiving criteria
remain unchanged until their outputs and observations exist.

The [component qualification index](../../verification/p07/native-components/qualification-index.json)
binds the final `dd31bed12de3133b30f0a06072ada37abd9f4961` worker source to 112 passing
tests without skips and ten passing quality/build/Terraform commands. Tests use
real PostgreSQL privilege/competition/reconnect boundaries, real TLS and subprocess
termination with synthetic platform responses. Terraform validates the module and
plans multiple workloads/NICs, quarantine and retained boot disks with a mocked
provider. No native installation, service enrollment or backup restore is claimed.
Earlier component results, failed image registration and simulation migration
integration runs remain retained. The image manifest now registers the read-only
entrypoint; native migrations reside under their own directory and database owner.
Strict JSON comparisons distinguish booleans from numbers, and observer expiry
requires an explicit timezone.

The [check matrix](../../verification/p07/check-matrix.md) and
[original evidence index](../../verification/p07/final/qualification-index.json)
record 105 preparation tests, isolated installed-command checks and separately
bounded P06 regression results. The
[remaining implementation and review packet](p07-completion-review.md) identifies
the actual inputs and native outputs still required for each package. No P07
package or G07 criterion is marked complete by the preparation campaign.


## API-first Console configuration

The Inventory/Console increment implements the existing ADR-015 baseline: API
pulls determine available options, installed/advertised features and configured
resources; administrators validate findings, explain interpretation overrides,
and supply non-discoverable inputs. Immutable revisions and confirmations bind
the selected source/destination generations. Raw observations never become
editable declarations or native support evidence. The [version register](openstack-version-qualification.md)
starts with 2026.2 Hibiscus and documents each API, collection boundary and remaining
native qualification. No new decision or approval is introduced.

Deployment inputs are runtime commissioning data. BL-P07-001 blocks native effects
and qualification that need an actual environment, not independent product or
adapter development. Existing N01–N15 preparation evidence remains original;
the checked-in unknown record is a template, not the Console configuration store.

The [configuration qualification](../../verification/p07/configuration/qualification-index.json)
and [check record](../../verification/p07/configuration/README.md) retain the
API-to-Console campaign, scoped PostgreSQL/collector tests, original failures and
source/hash comparisons. These exercise synthetic provider responses over real
TLS and database boundaries; they establish software behavior without qualifying
an installed OpenStack environment or completing native P07 operations.


## Durable native control and worker grant boundary

The [native workflow control](../operations/runbooks/native-workflow-control.md)
adds Lifecycle-owned immutable plans, resource/state-lineage holds, ordered
operations, one-time redemptions, append-only observations and a controlled job
projection. Actual owner authority is required at admission, preparation,
redemption and ongoing boundaries; the confirmed Console revision/digest,
plan/artifact/tuple, actor/workload, campaign, custody epoch and provider fence
must remain current. The database control starts empty and runtime cannot change it.

Mandatory readiness includes all eight enterprise services, backup restore,
application/data observations and exact positive/negative policy paths. Independent
provider quiescence is required after every effect. Partial or unknown observations
retain holds; old successful observations cannot clear a later hold. Stops prevent
further writes even after successful readback. Retirement requires a different
plan/approval, retention and readable retained data/keys, and independently
observed deletion before allocation release. None of these checks creates a real
service adapter, native observation or right to erase the worker's held claims.

The worker now implements `GrantedNativeAuthority` and a protected, pinned-TLS
Lifecycle client. The matching internal ASGI handler derives tenant and worker
from its trusted caller interface and rejects caller-supplied identities. Every
existing `NativeBinding` field is included in provision grants. Lost redemption
responses, stale authority, redirects and mismatched bindings cannot relaunch
Terraform. The [wire contract](../../contracts/openapi/lifecycle-native-boundary-v1.json)
and golden fixture are checked with the locked contract tools.

The [retained workflow qualification](../../verification/p07/native-workflows/qualification-index.json)
is E2 software evidence. The production composite owner adapter, workload-trust
composition, native Temporal dispatch, actual provider fencing and selected
service/effect/observer adapters remain unfinished. The simulation router does
not expose the native handler. Native commissioning and Q05/Q06 must still occur
on the selected environment. P07 remains IN_PROGRESS and G07 NOT_REVIEWED.
