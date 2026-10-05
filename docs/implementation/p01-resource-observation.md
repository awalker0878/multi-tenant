# P01 foundation resource observations

Scope: P01.06, G01.06. The Compose and Kubernetes recovery campaigns collect
bounded cgroup-v2 counters from all seven applications, seven TLS proxies and
PostgreSQL at the healthy-foundation and after-recovery checkpoints.

Each observation records UTC collection time, component and source revision;
CPU usage/user/system/throttling in microseconds; memory current/peak/limit in
bytes and OOM counters; current processes and process limits; and effective CPU
quota/period. Raw counter reads and their hashes remain in the campaign evidence.
Missing, malformed, duplicate or oversized observations fail the campaign.
An unlimited kernel setting is represented by null, never by zero or an invented
limit. A nonzero observed OOM-kill counter fails the checkpoint.

These are point-in-time measurements under synthetic diagnostics and recovery,
including measurement overhead. Counters are cumulative since each container
started. Replacement containers reset their own counters, so the two stages are
not subtracted or described as complete outage history. The measurements do not
establish capacity, production sizing, accepted objectives or SLOs.

Run the existing `scripts/p01/run_local.py` and `scripts/p01/run_kubernetes.py`
campaigns with their required exact source revision and an external evidence
directory. Inspect `resource_observations` in each resulting `report.json` and
the matching retained command logs. The same campaigns still perform actual
dependency-loss, persistence and failed-deployment recovery checks.

Correlated application logs/traces/metrics, collection-failure coverage and the
actual OP05 receiving route/response review remain separate obligations. This
increment addresses baseline resource cost only; it does not close all G01.06
conditions or imply an operating acceptance.
