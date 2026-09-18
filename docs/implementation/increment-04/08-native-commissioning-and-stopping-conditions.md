# Native commissioning and stopping conditions

[Documentation home](../../README.md) · [Source document](../../../Implementation_Execution_Guide.docx) · [Chapter index](README.md)

> **Source:** IMP04 — Implementation Increment 04. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9ca5c85333dcb51137ca694aea7b034e393fa8927831f0b475b3b88e842418f7 -->
<a id="chapter_8"></a>

[Contents and release status](01-implementation-increment-04.md#chapter_1)


<a id="source-table-87"></a>

| Hold point | Required implementation work before proceeding |
| --- | --- |
| 1. Toolchain | Verified Terraform and trusted plugins; actual source/schema/mock-plan checks. Python/source tests do not waive this gate. |
| 2. Target and authority | Select installed product/API/provider combination, disposable scope, exact origin/CA and read-only principal. No customer target was supplied or contacted in this release. |
| 3. Expected state | Accept native IDs, selected fields and real version/ETag/task/intent tokens independently. A response copied into its own expected record is not verification. |
| 4. Read and preserve | Run no-contact validation, then explicit scoped GETs with a fresh private output. No repair action is hidden in a reader. |
| 5. Interrupted work | Establish actual writer fencing and quarantine; retain containment, data and old evidence. Review current native progress and selected configuration before proposing another mutation. |
| 6. Independent verification | Assess actual packet paths, rule precedence, host placement, data access, DNS/identity/protection and failure behavior under the accepted profile. |
| 7. Service activation | Required initial operational/recovery readiness and applicable authorization precede production. No new tool sets service readiness or releases quarantine. |

## Local commands after extraction

```text
python tools/check_release.py
python tools/check_local.py
python lab/run_readback_lab.py --execute
python lab/run_dns_lab.py --execute
python lab/run_namespace_lab.py --execute
python tools/check_package.py
```

Run release integrity first: test commands intentionally refresh quality files. The local labs accept only their bounded fixtures. Runtime readers use the standard library; fixture certificates use the retained tested cryptography dependency. Existing DNS and packet tests need the documented additional libraries and Linux namespace tools.

[Commissioning sequence](../../COMMISSIONING.md)

[Native operation and integration backlog](../../../sources/implementation_backlog.csv)

[Previous chapter](07-local-execution-and-observed-results.md) · [Chapter index](README.md) · [Next chapter](09-primary-native-interface-sources.md)
