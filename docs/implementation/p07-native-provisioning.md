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
