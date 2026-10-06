# P06 failed observations and corrections

Failed runs remain failed. The [archive index](failures/archive-index.json)
retains selected original archives and their SHA-256 digests; reports are copied
without altering observations. The final qualification index identifies the later
complete run and does not relabel an earlier partial campaign as a pass.

| Observation | Correction |
| --- | --- |
| Initial image and package regressions after adding owned runtime dependencies; Compose run 37512315239 rejected the Lifecycle entrypoint. | Declare exact locked runtime requirements for Lifecycle and its worker, install those dependencies, and preserve the health-first declared entrypoint. P01 lock/image controls continue to validate exact closure. |
| Governance recovery fixture retained the pre-P06 workload map. | Include the new Lifecycle audience in both fixture and recovery ceremony; preserve current workload revocation semantics. |
| P06 run 37512315307 could not create Temporal schema because the pinned admin image was absent under `pull_policy: never`. | Explicitly pull every pinned image before starting the disposable fixture. |
| P06 run 37512933216 could not reach the host-published Temporal frontend, and cleanup after private-directory deletion masked the final report. | Make only the loopback-published workflow bridge host-reachable, retain private database networking, and capture/close Temporal before deleting private inputs. Original partial logs remain in the archive. |
| P06 run 37513710979 received Lifecycle 503 on first admission. | Grant runtime USAGE on the installer-owned app schema in the live fixture, matching actual deployment and the existing core fixture. |
| P06 run 37514549875 reached the real acceptance crashes but expected 201 for reader membership upsert. | Assert the owner's documented 200 response. |
| P06 run 37515335960 passed Jobs controls, real dispatch recovery and evidence outage, then expected 403 for revoked membership. | Assert Governance's intentional 404 tenant-concealment response; no authority rule was relaxed. |
| Context run 37515335859 found the Lifecycle README's new runbook link before the runbook commit. | Publish the complete runbook and review packet; clean-source documentation, architecture and generated-view checks passed. |
| P06 core run 37516350056 passed 48 cases, then the new connection-loss fixture supplied a duplicate `connect_timeout` keyword. | Use the database adapter's existing bounded timeout. Retain the original failure and rerun the actual refused-connection observation. |
| Kubernetes run 37515335885 received empty stdout with exit 0 from its second-process shared-state witness. | Preserve the original archive and exact empty witness as failed evidence. A later deployment campaign must independently pass; no successful state or root cause is inferred from empty output. |
| Inventory regression run 37513710639 attempt 1 stopped the Chromium campaign at `broker_not_ready`. | Retain the original failed archive and retry the failed job with unchanged Inventory/Governance/Console/P04 inputs. Successful Firefox, WebKit and PostgreSQL results remain separately recorded. |

Additional implementation checks identified receipt recovery after input expiry,
projection freshness on acquisition, ownership recheck at grant redemption and
separate evidence-page authorization polling. Their corrections are covered by
the final source-bound campaign. Earlier local PostgreSQL skips are limitations,
not failed or passing integration results.

The [regression completion receipt](final/regression-completion.json) records the
later final-source Kubernetes pass, the successful Inventory retry and all carried
source-impact comparisons. Earlier failures retain their original status and bytes.
