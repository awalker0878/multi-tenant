# P04 qualification corrections

Original failures remain failures. Later results qualify only the later recorded
source. Synthetic native peers do not provide E3 installation acceptance.

| Source / check | Finding | Corrective work |
| --- | --- | --- |
| Local initial PostgreSQL attempt | The managed workspace maps only root and cannot start PostgreSQL under an unprivileged service identity. Seventeen database setup errors supplied no persistence evidence. | Use the actual unprivileged hosted PostgreSQL/TLS campaign; retain local skips explicitly. The first hosted core run `37433829615` at `8290f144` passed 70 tests. |
| Local Governance integration | New Inventory roles were absent from the HTTP audience validator and existing database CHECK constraint; recovery fixture workload maps omitted the new credential. | Add constrained validation and additive `012_inventory_delegation.sql`; keep the recovery credential rotation boundary strict and update its explicit fixtures. Actual PostgreSQL and recovery regression run `37436983548` passed. |
| `8f73a44d`, foundation package selection | The runtime closure test still expected the old Inventory dependencies and rejected pinned pika 1.4.4. | Add this exact Inventory dependency to the expected production closure. All nine package jobs passed at `9cfb9d70` (`37437859218`). |
| `9cfb9d70`, image/Compose/Kubernetes | Image input registry rejected the added publisher dependency and worker command. | Explicitly declare pika and the owned collector command; preserve empty worker dependencies, source ownership, health default entrypoint, isolated build and immutable runtime checks. |
| `9cfb9d70`, live P04, all three engines | The new harness replayed every historical migration, including the Catalogue initial messaging schema that is not independently replayable. The campaign stopped before product requests. | Apply baseline schemas once and replay the new Inventory migrations and additive Governance delegation migration. No product migration was weakened. |
| `3ab6d72f`, live P04 | The site-owner fixture queried an incorrect role name and stopped before enrollment. | Resolve the actual seeded `tenant_admin` membership and preserve the independently checked owner identity. |
| `fb37bb22`, live P04 | All 48 pre-browser checks passed, but the reused principal fixture invalidated its administrator session when creating the author session. The browser correctly redirected to login. | Give each browser a separate session store and independently require two persisted sessions. No login or authorization rule was relaxed. |
| Scheduler/source review | An unavailable tenant's current authority could repeatedly win selection and prevent another eligible tenant from receiving a lease. | Persist a five-second hold for that job without allocating a lease; test shared-worker progress and concurrent tenant budgets across authorities. |
| Discovery/source review | An expired early page could leave final publication retrying, and terminal transport failures lacked a terminal event. | Finish the scan as partial without replacing current observations; atomically record terminal failure facts. Test original event identity/order after uncertain publication. |
| Matching/source review | A visible ownership collision disabled the Console button but the API could accept further proposals. | Apply the same hold in the owning service and exercise direct-command denial after the collision. |

The final qualification index and source bindings identify which corrective source
was actually executed. Neither a passing process liveness diagnostic nor a passing
synthetic no-change observation implies native readiness or G04 acceptance.
