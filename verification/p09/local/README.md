# P09 partial local verification

**Result: PARTIAL. P09, G09 and native acceptance remain open.**

The [qualification index](qualification-index.json) retains the original
[component report](report.json), original logs and JUnit outputs. It binds current
source `1a9fd01f23a40f148467eacefffb0befadb5469d` to component checks executed at
`86fb17a7154caa23dd4f67728bc6b068f518d111`. Every bound component source file is
unchanged; only the P09 campaign's architecture-check ordering changed afterward.

| Component | Passed | Skipped | Failed / errors |
| --- | ---: | ---: | ---: |
| Planning | 303 | 5 | 0 |
| Lifecycle | 301 | 59 | 0 |
| Lifecycle worker | 277 | 15 | 0 |
| Total | 881 | 79 | 0 |

All three locked dependency installs, lint checks, formatting checks, strict type
checks and wheel builds succeeded. Schema conformance succeeded. TLS tests use
actual local TLS connections and synthetic native responses. Test names and exact
skip reasons are retained in the report and the three JUnit files.

The original architecture command failed because the wheel builds generated
`build/lib` source copies under the three component directories. The strict gate
correctly rejected those unregistered copies. The P09 campaign now runs architecture
validation before building wheels. Only the generated directories were moved out
of the checkout; the unchanged architecture validator then passed. Both the original
[failure](architecture.log) and [corrected check](architecture-corrected.log) remain
retained with hashes. No architecture rule or source-layer boundary was relaxed.

PostgreSQL is unavailable in this environment and switching to its unprivileged
database account is blocked. All 79 PostgreSQL-dependent cases remain **unexecuted**.
The complete `scripts/p09/qualify.py` campaign rejects skips and has not passed.
Automatic approval review rejected the public branch push needed to start the
prepared GitHub-hosted PostgreSQL campaign; no alternate publication was attempted.

These local component observations do not establish selected native effects,
provider identity/fencing, an installed platform tuple, a migration direction,
G09 receiving, or operational acceptance. Actual tranche selection, native owner
inputs, integration and independent campaigns remain in the
[completion packet](../../../docs/implementation/p09-completion-review.md).
