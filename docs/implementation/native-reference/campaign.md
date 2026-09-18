# Native observations and evidence collection

**NRC-M01 supporting procedure — Proposed.** The existing W14 assertion IDs and their
original CT mappings remain authoritative; this kit adds run-sheet preparation, not a
new count of independent controls or a results database.

## Select actual applicability before scheduling a test

Read [W14 observations](../../solutions/internal-protected-workload/13-verification-assertions-and-actual-evidence.md),
[the four existing families](../../assurance/verification-families.md) and the selected
site's accepted service/failure scope. First-platform G2 can complete without a second
stack. W14-12 belongs to the later representative equivalence/exit scope, not a circular
prerequisite to first-platform qualification. An address family or failure class that is
not offered requires a recorded applicability decision; it is not a passed observation.

| Run-sheet group | Native observations to prepare |
| --- | --- |
| W14-01 | Every domain/edge/service next hop and reply; actual forwarding, enforcement and bypass review |
| W14-02 | Approved endpoint plus specific entitled operation; deny admin and another tenant's endpoint/resource |
| W14-03 | Actual delegated role cannot replace mandatory controls or create an alternate attachment/path |
| W14-04 | Allocation, routes, local controls, MTU/PMTU, service replies and recovery for each offered family |
| W14-05 | Approved resolver UDP, direct TCP, truncation/fallback and unauthorized resolver path |
| W14-06 | Scoped additional probe, same-host/cross-host paths when eligible, positive and negative controls |
| W14-07 | Commitments and temporary/recovery demand against each measured surviving resource limit |
| W14-08 | Lost executor, native task/resource discovery, real writer exclusion and no duplicate effect |
| W14-09 | Independent initial readiness and authority dependencies before a production change |
| W14-10 | Selected shared-service/control/edge loss with retained policy, bounded impact and recovery |
| W14-11 | Useful retained data, catalogue/key recovery, independent deletion authority and safe retirement |
| W14-12 | Equivalent declared service plus representative useful-data recovery/exit on a second eligible stack |

## One attempt must be unambiguous

Use a unique attempt ID and record assertion/procedure variant, exact platform tuple,
topology generation, actual native resource references, address family, placement,
direction, observed protocol/operation, source credentials by reference (never value),
start/end time and control result. A single aggregate W14 row is not enough when multiple
families, placements, failure variants or attempts are applicable: duplicate the blank
worksheet row for each one and keep their identities separate.

Capture native configuration and effective enforcement/forwarding evidence, client and
service observations, event attribution and actual data/copy identity when relevant.
Keep original artifacts in the approved evidence store with provenance, timestamps,
access controls and retention. A CSV artifact reference or recomputed digest does not
authenticate the collector, signer, scope or operating authority.

## Test a denial against a functioning environment

Before a negative assertion, demonstrate a healthy source, a healthy intended target
and an approved positive control that distinguishes unrelated outage. Correlate the
result with the intended enforcement point. A timeout can be blocked or inconclusive;
it is not automatically a security success. Record absence of routing separately from
policy denial. Demonstrate established reply behaviour separately from unsolicited
reverse initiation.

The base fixture has one endpoint per domain. That cannot by itself prove every
intra-domain/same-host control. Reserve an additional scoped probe where needed,
place it only on eligible hosts, document its identity and remove it after its tests.
Do not test against an unrelated tenant to avoid provisioning a controlled probe.

## Use readback without inflating its meaning

The existing [NSX](../../../tools/nsx_observe.py), [Nutanix](../../../tools/nutanix_observe.py)
and [Neutron](../../../tools/neutron_observe.py) tools only observe their documented
selected resources. Native IDs and expected version/task scope must come from the
accepted writer record. These readers neither discover all applicable policy nor
prove every packet path. Do not replace missing fields with assumed false/empty values,
a 404 with retirement proof, a completion percentage with task success, or a succeeded
task with a correct resource graph.

The [offline recovery reviewer](../../../tools/recovery_review.py) has no authority to
fence a real writer, release containment, replay, delete or activate. Obtain those facts
from the responsible native owner and preserve uncertainty when they cannot be shown.

## Result handling and release

Record passed, failed, blocked, not run, or not applicable with its accepted rationale
in the actual governed campaign. A recovered failed attempt remains in history; a later
success is another attempt, not an overwritten report. A failed/unknown positive control
makes the associated negative claim inconclusive. An applicable failed mandatory
assertion prevents the related service acceptance until resolved under the actual process.

Review the evidence under its current tuple and topology; identify changes that require
new tests. Keep G2 offered-capability acceptance, applicable initial G4 readiness and
G3 production authority distinct. The local exporter cannot validate filled results or
produce an acceptance token. CI in this repository executes only its separately scoped
local/engine checks and must never receive the actual native campaign credentials.

[Kit index](README.md) · [Recovery and teardown](recovery-retirement.md)

## Local packet observations versus this native campaign

The existing [routed IPv6 and retained IPv4 campaigns](../routed-ipv6-lab.md) can develop
procedure variants and failure probes. Their Linux namespace identities, PMTU witness
and local TLS grants are not the installed native tuple, actual policy or recovered data
required by the W14 campaign. Do not prefill a native observation row with their PASS
labels. Preserve the separate source/run evidence and collect actual applicable site
observations only within that site's accepted scope.
