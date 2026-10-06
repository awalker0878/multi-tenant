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
files, with value-free errors. No new runtime dependency or HTTP surface is added.

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

Actual installed tuples, interfaces and tooling remain unsupplied in ADR-015/016
and the retained feasibility/operating inputs. Native infrastructure, allocation,
guest/service adapters, quarantine activation, native failure/restore/retirement
and the reviewed native support dossier are not delivered by this preparation.
P06 continues to expose simulation only. A metadata checker is neither an OpenStack
adapter nor a substitute for the independent Q05/Q06 campaign.
