# Foundation alert and failed-deployment recovery

P01.06 development procedure. Use only the generated isolated installation and its
synthetic credentials; native writes remain disabled. The recorded campaign source
and image identities identify the exact rehearsal, not an operated service.

1. Install the pinned Compose or Kubernetes inventory using its existing campaign.
   Confirm the owned database/migrator identity, authenticated dependency health,
   unavailable product readiness and fixture rows before injecting a fault.
2. For Console, run the owner session/cache migration before installing replicas.
   Retain the Console database and its separate application key together. Cache
   content is disposable; sessions require the original key for continued use.
3. The Compose campaign stops PostgreSQL and measures actual unavailable dependency
   health while process liveness survives. For each observed failure, send the
   allowlisted alert over verified HTTPS to the synthetic authenticated receiver.
   Inspect the separately received event and its matching acknowledgement ID.
   Sender success alone is insufficient. Redirects, unexpected payload fields and
   unacknowledged delivery fail the test. No email/chat message is sent.
4. Restart PostgreSQL, compare foundation records and shared Console state, restart
   Console and compare again. Inject an invalid Console application-key configuration;
   require an actual failed page request. Restore the exact prior configuration,
   reload the process and verify the existing encrypted session and tenant caches.
5. In Kubernetes, deploy a new Console template whose process exits 42. Require both
   failed rollout status and the observed container exit. Roll back through Deployment
   revision history, wait for the prior template to become ready, recheck authenticated
   health and compare database records. Do not rebuild or substitute a new artifact
   while describing the operation as a rollback.
6. Retain source/image/command hashes, observed results, correlation/receipt IDs and
   cleanup. Remove only the generated project/cluster. Do not retain mounted keys,
   passwords or bearer tokens in the evidence directory.

The in-process receiver independently acknowledges network delivery for the synthetic
campaign. It is not an on-call operator acknowledgement, paging-provider integration
or operational acceptance. Supply the actual receiving route, identities and response
ownership before operated alert qualification. Full P10 recovery, HA and customer
RPO/RTO remain outside this bounded rehearsal.

The measured executions are EV-P01-016 (Compose run `37259472748`, 149 top-level
checks) and EV-P01-018 (Kubernetes run `37260680483`, 166 top-level checks).
Their [shared-state record](../../implementation/p01-console-shared-state.md) links
retained reports, source bindings and recovery observations. The Kubernetes run
also replaces the Console Pod and checks the original session/cache after rollback.
