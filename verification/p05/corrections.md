# P05 qualification corrections

Original failed observations remain failed. Later passing observations qualify
only their recorded source and environment. Raw failure reports, logs and original
ZIP archives are retained under `failures/`. Isolated package raw logs and bound
manifests use the established `verification/p01/packages/run-37466956477/` location.

| Source / observation | Finding | Correction and verification boundary |
| --- | --- | --- |
| `55b03c1`, isolated package run `37466956477` | New Planning/Lifecycle/Governance tests read repository-level fixtures absent from an isolated component. Raw logs contain FileNotFoundError / file_get_contents failure. | Own exact test copies within each component and check drift in the P05 contract generator. All nine packages passed at `6051eac`; final-source packages are recorded separately. |
| `6051eac`, contract run `37469317907` | A correction changed the already published synthetic plan fixture in place. Immutable contract admission correctly rejected it. | `290b859` restores original v1 bytes and adds corrected v1.1. The restoration itself differs from the erroneous immediately preceding commit, so that transitional comparison also remains a failure. Later qualification compares the restored immutable baseline; no compatibility rule or expected digest is weakened. |
| `6051eac`, P04 WebKit regression `37469317836` | Broker container did not reach readiness; campaign stopped before browser execution. The other two engines passed. Existing retained output does not establish the container exit cause. | Add failure-only broker state/server diagnostics without changing timeout or readiness criteria. All three P04 engines subsequently passed at `8ad4e85`; final receipts retain source boundaries. |
| Source review, corrected in `c045bad` | Testing an unqualified lab tuple could return a qualification-only finding before evaluating stale/unsupported observations or unresolved dependencies. | Evaluate observation safety independently before qualification; five targeted cases retain non-waivable safety reasons. Operational behavior remains fail closed, and admission still requires bounded lab authority. |
| `c045bad`, WebKit job `112295651149` | The unchanged 20-minute job limit was reached during slow Ubuntu dependency downloads; no product or browser case ran and no campaign artifact existed. | Retain the complete job log and retry this job alone at the same source; browser case retry settings and timeouts are unchanged. |
| Evidence reconciliation | Live setup regenerates Inventory SOURCES and Planning SOURCES/PKG-INFO after locked installation, so these three observed metadata hashes differ from their committed snapshots. | Independently reconstruct all three exact hashes from a clean exact-source component copy using the locked build toolchain; retain original/observed hashes and rebuilt bytes separately. Every product-source hash still matches the commit directly. |
| Local PostgreSQL boundary | The managed workspace cannot start an unprivileged PostgreSQL service; local database cases remain explicit skips. | Real hosted PostgreSQL/TLS campaigns execute the database cases without skips. Local unit success is never substituted for those results. |

No native effects, real installed qualification, reviewer identity or operating
acceptance is inferred from these corrections or passing liveness probes.
