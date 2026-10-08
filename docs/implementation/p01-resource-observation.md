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

## Retained measurements

EV-P01-025/026 retain 179 Compose and 196 Kubernetes checks at `b7705eef994c50863d87b4d8f9ff272f9397ca37`.
Both runs completed cleanup and supplied 30 samples (15 containers at each of
two stages), with zero observed OOM kills. The original archives, exact reports
and source/log verification are available in the [Compose record](../../verification/p01/local/run-37272826323/retrieval.json)
and [Kubernetes record](../../verification/p01/kubernetes/run-37272826200/retrieval.json).

The table reports memory.current in MiB at each checkpoint; reads are sequential
and include synthetic workload/measurement overhead. These are not host-RAM
requirements. CPU, process and effective-limit details remain in the raw reports.

| Component | Compose healthy | Compose recovered | Kubernetes healthy | Kubernetes recovered |
| --- | ---: | ---: | ---: | ---: |
| console | 38.69 | 37.07 | 19.04 | 35.50 |
| governance | 30.88 | 30.71 | 18.92 | 33.95 |
| catalogue | 31.62 | 31.06 | 18.85 | 35.22 |
| assurance | 30.93 | 30.46 | 18.84 | 33.71 |
| planning | 27.53 | 27.73 | 27.26 | 27.57 |
| inventory | 27.44 | 27.69 | 27.61 | 27.45 |
| lifecycle | 27.71 | 27.78 | 27.24 | 27.83 |
| postgres | 173.84 | 38.40 | 176.56 | 39.62 |
| console-proxy | 4.48 | 4.24 | 3.89 | 4.32 |
| governance-proxy | 4.14 | 4.34 | 4.14 | 4.11 |
| catalogue-proxy | 4.16 | 4.35 | 3.50 | 3.91 |
| assurance-proxy | 4.45 | 4.24 | 4.15 | 4.15 |
| planning-proxy | 4.25 | 4.46 | 3.78 | 3.83 |
| inventory-proxy | 3.92 | 4.09 | 4.00 | 3.82 |
| lifecycle-proxy | 3.78 | 4.58 | 3.73 | 4.26 |

Compose reports unlimited effective CPU/memory/process limits. This is an explicit
remaining OP01 budget decision, not an accepted production configuration.
