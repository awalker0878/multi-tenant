# 13. Verification assertions and actual evidence

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Chapter index](README.md)

> **Source:** WD — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e4a2e42888349b5967f7b3174c78e53171728b13e99e4c78bc3cfb53310f68db -->
<!-- SOURCE-BLOCK WD:133 BEGIN -->

<a id="WD14_S13"></a>

<!-- SOURCE-BLOCK WD:133 END -->

<!-- SOURCE-BLOCK WD:134 BEGIN -->

The assertion IDs below are additions to the architecture verification plan, not renamed or pre-passed CT tests. The inherited 80 CT procedures and 12 realization addenda remain unchanged as historical specifications and remain not-run in this release. Applicability and actual evidence must be recorded for the selected topology.

<!-- SOURCE-BLOCK WD:134 END -->

<!-- SOURCE-BLOCK WD:135 BEGIN -->

For a denied-path test, demonstrate healthy endpoints and a permitted control path. For a routing claim, compare both intended routing and actual forwarding/enforcement. For a recovery claim, validate useful recovered data and all necessary trust dependencies. A successful Terraform process verifies none of these by itself.

<!-- SOURCE-BLOCK WD:135 END -->

<!-- SOURCE-BLOCK WD:136 BEGIN -->

Record each result as passed, failed, blocked, not run, or not applicable with its approved rationale. The evidence names the exact component tuple, topology, observed state, time, owner, procedure and artifact. No support declaration, example address or architecture diagram supplies an observed result.

<!-- SOURCE-BLOCK WD:136 END -->

<!-- SOURCE-BLOCK WD:137 BEGIN -->


<a id="source-table-137"></a>

| Assertion | Required observation | Existing procedure families / status |
| --- | --- | --- |
| W14-01 / routing completeness | Every domain, edge, service next hop and return path matches the approved schedule. | CT-003, CT-009, CT-023, CT-024 / NOT RUN |
| W14-02 / service isolation | Only named service endpoints and authorized resource scope are reachable; router/admin and other tenant targets deny. | CT-004, CT-008, CT-037 / NOT RUN |
| W14-03 / mandatory policy authority | Tenant roles cannot attach a permissive group, disable port security or create an alternative native path. | CT-019, CT-020, CT-022, CT-066 / NOT RUN |
| W14-04 / family completeness | Each offered address family has working allocation, routes, service replies, local controls and recovery. | CT-002, CT-031, CT-032 / NOT RUN |
| W14-05 / DNS completeness | UDP, direct TCP and truncation/fallback work only against approved resolvers. | CT-008 plus explicit protocol observations / NOT RUN |
| W14-06 / intra-domain fixture | Temporary probe verifies same-host and cross-host controls where that placement is approved. | CT-021, CT-035 / NOT RUN |
| W14-07 / admission accounting | Compute, data, context, service and edge commitments fit the same accepted failure basis. | CT-039, CT-056, CT-074 / NOT RUN |
| W14-08 / lost executor | Accepted native tasks and side effects are discovered; no duplicate allocation or competing writer appears. | CT-044, CT-045, CT-046 / NOT RUN |
| W14-09 / activation dependencies | Production activation rejects missing applicable operating or promised recovery readiness. | CT-062, CT-069 plus G3/G4 review / NOT RUN |
| W14-10 / shared-service failure | Permitted and denied paths retain the selected policy and declared service behavior during approved failure. | CT-011, CT-012, CT-024, CT-050 / NOT RUN |
| W14-11 / retained recovery | Required copy, catalogue and key access survive live WSD retirement; unauthorized destruction denies. | CT-051, CT-052, CT-053, CT-078 / NOT RUN |
| W14-12 / second-stack outcome | Repeat the declared environment and representative data recovery on a second eligible stack. | CT-016, CT-060, CT-073 / NOT RUN |

<!-- SOURCE-BLOCK WD:137 END -->

<!-- SOURCE-BLOCK WD:138 BEGIN -->

<!-- SOURCE-BLOCK WD:138 END -->

<!-- SOURCE-BLOCK WD:139 BEGIN -->

Related documents: [QUAL — Applicability and observed results](../../assurance/site-qualification/README.md#V14_QUAL_START)  \|  [GM — Open evidence and decisions](../../assurance/gap-map/README.md#V14_GM_START)

<!-- SOURCE-BLOCK WD:139 END -->

<!-- SOURCE-BLOCK WD:140 BEGIN -->

<!-- SOURCE-BLOCK WD:140 END -->

[Previous chapter](12-failure-and-partition-decision-schedule.md) · [Chapter index](README.md) · [Next chapter](14-remaining-decisions-and-release-boundaries.md)
