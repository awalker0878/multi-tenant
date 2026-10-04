# Enterprise wave budgets and tenant turns

The B43 enterprise owner enrolls one immutable aggregate budget over existing
tenant wave domains. It admits the original B09 job and outbox in the same
transaction as the original wave member. It creates no second queue or native
execution authority.

`provisioner.migration.enterprise_wave_commissioning.EnterprisePoolCommissioner`
reads each tenant's actual original aggregate budget observation through retained
evidence custody, checks its exact bytes and verifies a separate current Vault
budget signature for that tenant. Its database connection must be the independent
non-superuser, non-bypass schema owner. Native pool enrollment is external
commissioning; the worker and HTTP application roles cannot insert or update it.

| Admission condition | Database enforcement |
| --- | --- |
| Exact enrolled domains | Original tenant/domain digests and complete local-to-physical risk maps |
| Aggregate resource budget | Concurrent jobs, exposed workloads, downtime, risk units, staging bytes, transfer bandwidth and IOPS |
| Physical shared risk | Every local risk group maps to one explicitly capped physical group |
| Native resource overlap | Original resource keys across all enrolled tenant domains |
| Tenant turn | One eligible ticket per verified organization/tenant, round-robin after the last admitted tenant |
| Current eligibility | Original pending member, bounded current authority and complete execution window |
| Uncertain original work | Every admitted/held charge persists until original independent accepted release |
| Transaction failure | Job, outbox, member, turn and claims roll back together |

An eligibility ticket lasts at most thirty seconds. Expiry removes only scheduling
eligibility; it never frees a job's resources or decides a native outcome. A
temporarily unfit ticket is skipped when choosing the next tenant turn. Existing
within-tenant scheduling still rotates security domains. A domain outside an
independently enrolled pool retains its original local scheduling behavior.

Migration `0030_enterprise_wave_pools.sql` gives no role table privileges. The
tenant service needs only `EXECUTE` on
`hosting_controlplane.migration_wave_pool_turn(text,text,text,text,text,text,timestamptz)`
in addition to its existing wave permissions. Reviewed definer functions can
aggregate only scheduling tables; the caller receives a boolean and cannot read
another tenant's members, tickets, native bindings or job history.

Local model and signature/custody negatives are in
`tests/provisioning/mobility/test_enterprise_wave.py` and
`test_enterprise_wave_commissioning.py`. Actual separate-role PostgreSQL races,
budget retention, tenant turns and transactional failure are in
`test_enterprise_wave_postgres.py`. Isolated fixtures are explicitly synthetic;
they do not qualify native concurrency, estate throughput or an application
migration. Those campaigns need separate directed evidence on the final installed
code and commissioned native budget.
