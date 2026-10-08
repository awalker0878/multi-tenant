# P08 component check matrix

Qualified software source: `a72d0e88b3626b6912cf189c46ce45cf2fc4878c`.
The [index](qualification-index.json) binds original ZIPs, reports, command logs,
source hashes and JUnit outcomes. Run `python scripts/p08/verify_retained.py`
from a checkout containing the referenced Git objects to verify those bindings.

| Surface | Measured behavior | Evidence boundary |
| --- | --- | --- |
| Inventory source/target components | Immutable VM identity/config drift; disk/backing/controller mappings; source capabilities and unsupported-feature holds; observed OpenStack formats, limits and versions | Synthetic native responses; no installed API profile or Console integration |
| Capture | Stopped source, disk-only S0, exact-snapshot clone, NIC/media removal before creation, task receipts and ambiguity holds | Synthetic VI JSON peer; no native VM created |
| NFC/OVF archive | Real TLS transfer, byte/rate/deadline budgets, native manifest matching, descriptor findings and safe complete mappings, descriptor before lease completion, retained interruption state | Synthetic disk stream and native API responses |
| Conversion | Copy-only RAW/QCOW2 command sequence, supported VMDK subtype, source hash preservation, virtual size/metadata/check/sector comparison, output bounds, exact artifact handoff | Synthetic QEMU command engine; no real converter rootfs or guest boot |
| Converter launcher | Real subprocess file/output/deadline limits from a worker thread; cancellation containment | Python child process; does not qualify QEMU or bubblewrap |
| Glance import | Actual TLS, exact image ID/format/metadata and sha512, all-disk checks before creation, no method fallback after lost or failed stage | Synthetic Glance peer and image bytes; no installed image backend |
| Worker custody | Real PostgreSQL append-only generations, stale/cross-scope denial, same-job capture/artifact resolution, complete all-disk digest, no late-disk acceptance | Disposable database; site-owned custody and provider fencing remain uncommissioned |
| Migration control | Explicit method/stages, profile/plan/epoch checks, cold and delta order, rehearsal suppression boundary, atomic first-possible-write marker and higher-generation separately approved recovery | Real PostgreSQL, synthetic current owners/observations; no application cutover |
| Recovery ancestry | Superseded-job stop, rejected stale activation, pre-write rollback versus accepted/uncertain-write forward/reverse recovery across prior jobs | Control invariants only; no native guest/database recovered |
| Contracts | Version 2 migration grant/effect schemas, positive fixture, eight negative variants and exact worker/coordinator stage-set comparison | Published v1 provision contract remains unchanged |

The final component run executes 20 commands, verifies 262 source bindings and
passes 295 Lifecycle, 204 worker and 59 Inventory-worker tests without skips.
The earlier control checkpoint passes 295/155/58. The intermediate data-path run
has 295/193/59 passing tests but a **failed strict type check**; its overall result
remains FAILED. See [corrections](corrections.md).

No Q07 case is claimed as an E3 pass. No native platform, guest transformation,
application dataset/delta, enterprise service, provider fence, traffic switch,
post-write data recovery, G07/G08 review or operating acceptance is supplied.
