# P08 migration operations implementation

The remaining P08 work includes environment/account commissioning, complete native
journey composition, performance measurement, concurrency, staggered schedules and
operator control. This record supplements the existing P08 packages; it does not
change the native-only baseline or mark G08 accepted.

## Campaign control increment

Lifecycle owns migration campaigns, ordered plan references, UTC windows with an
IANA display zone, separate cutover windows, blackouts, staggered starts, phase
limits, failure limits and durable resource allocations. A schedule never supplies
execution authority. Native admission and every effect still require current
owners, exact reviewed plans, independent observations and existing custody.

The campaign domain checks cycles, missing dependencies and entire-window fit.
Performance estimates use the slowest current comparable measured sample for each
stage, add a 25% time margin and refuse unmeasured concurrency or stale routes.
Transfer throughput is not substituted for conversion/import throughput. A recent
production-impact breach holds the corresponding phase.

Migration campaign assignment and native job admission share one PostgreSQL
transaction. Capacity is counted across outstanding allocations, including unknown
outcomes. Stage slots are released only after the existing independent post-effect
observation. Completion does not release staging/rollback retention. Cancellation
removes queued starts and preserves active native jobs and their custody; native
stop/recovery remains an explicit separate operation.

This increment implements the domain and transactional integration. Authenticated
campaign endpoints, actual measured sample publication, independent capacity
publication, connection commissioning, complete Planning composition and the
Console journey are subsequent required integration work. Browser-supplied claims
must never serve as measured rates, native capacity, current owner evidence or
secret values.

## Remaining scope to close

1. Configure each source/target account through approved endpoint and secret custody;
   test actual permissions, rotation, revocation, worker placement and connectivity.
2. Complete source profile and native plan composition, real guest/converter/data/
   service/fencing/traffic/recovery adapters and the native runtime bootstrap.
3. Implement reconciled large-transfer continuation beyond the 600-second activity.
4. Publish authenticated performance and pool observations and integrate resource
   reservation, dynamic stage admission, wave dispatch, monitoring and Console controls.
5. Qualify fleet partitioning and group scale without silently widening endpoint scope.
6. Run software, PostgreSQL, browser and workflow campaigns; retain original failures
   and corrections. Then execute Q05/Q06/Q07 on the actual commissioned VMware and
   OpenStack tuple, including both data recovery boundaries and accepted objectives.

Actual identities, installed platforms, owners' application protocols and native
Q07/G08 receiving results remain external inputs. Unknown or missing inputs remain
explicit holds. No software result can stand in for those observations.
