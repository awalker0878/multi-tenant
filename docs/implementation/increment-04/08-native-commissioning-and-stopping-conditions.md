# Native commissioning and stopping conditions

[Documentation home](../../README.md) · [Source document](../../../Implementation_Execution_Guide.docx) · [Chapter index](README.md)

> **Source:** IMP04 — Implementation Increment 04. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9ca5c85333dcb51137ca694aea7b034e393fa8927831f0b475b3b88e842418f7 -->
<!-- SOURCE-BLOCK IMP04:85 BEGIN -->

<a id="chapter_8"></a>

<!-- SOURCE-BLOCK IMP04:85 END -->

<!-- SOURCE-BLOCK IMP04:86 BEGIN -->

[Contents and release status](01-implementation-increment-04.md#chapter_1)

<!-- SOURCE-BLOCK IMP04:86 END -->

<!-- SOURCE-BLOCK IMP04:87 BEGIN -->


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

<!-- SOURCE-BLOCK IMP04:87 END -->

<!-- SOURCE-BLOCK IMP04:88 BEGIN -->

## Local commands after extraction

<!-- SOURCE-BLOCK IMP04:88 END -->

<!-- SOURCE-BLOCK IMP04:89 BEGIN -->

```text
python tools/check_release.py
```

<!-- SOURCE-BLOCK IMP04:89 END -->

<!-- SOURCE-BLOCK IMP04:90 BEGIN -->

```text
python tools/check_local.py
```

<!-- SOURCE-BLOCK IMP04:90 END -->

<!-- SOURCE-BLOCK IMP04:91 BEGIN -->

```text
python lab/run_readback_lab.py --execute
```

<!-- SOURCE-BLOCK IMP04:91 END -->

<!-- SOURCE-BLOCK IMP04:92 BEGIN -->

```text
python lab/run_dns_lab.py --execute
```

<!-- SOURCE-BLOCK IMP04:92 END -->

<!-- SOURCE-BLOCK IMP04:93 BEGIN -->

```text
python lab/run_namespace_lab.py --execute
```

<!-- SOURCE-BLOCK IMP04:93 END -->

<!-- SOURCE-BLOCK IMP04:94 BEGIN -->

```text
python tools/check_package.py
```

<!-- SOURCE-BLOCK IMP04:94 END -->

<!-- SOURCE-BLOCK IMP04:95 BEGIN -->

Run release integrity first: test commands intentionally refresh quality files. The local labs accept only their bounded fixtures. Runtime readers use the standard library; fixture certificates use the retained tested cryptography dependency. Existing DNS and packet tests need the documented additional libraries and Linux namespace tools.

<!-- SOURCE-BLOCK IMP04:95 END -->

<!-- SOURCE-BLOCK IMP04:96 BEGIN -->

[Commissioning sequence](../../COMMISSIONING.md)

<!-- SOURCE-BLOCK IMP04:96 END -->

<!-- SOURCE-BLOCK IMP04:97 BEGIN -->

[Native operation and integration backlog](../../../sources/implementation_backlog.csv)

<!-- SOURCE-BLOCK IMP04:97 END -->

<!-- SOURCE-BLOCK IMP04:98 BEGIN -->

<!-- SOURCE-BLOCK IMP04:98 END -->

[Previous chapter](07-local-execution-and-observed-results.md) · [Chapter index](README.md) · [Next chapter](09-primary-native-interface-sources.md)
