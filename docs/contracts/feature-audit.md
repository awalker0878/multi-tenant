# Current contract feature audit

The contract platform has strong source and packaging integrity but incomplete
runtime qualification. Its required assurance gate correctly fails when execution
proof is missing. Passing schema validation, SQL/browser journeys, or image parity
does not establish every operation's consumer behavior or current authority.

## Capabilities and verified limits

| Capability | Current implementation | Limit that remains |
| --- | --- | --- |
| Canonical ownership | 75 active releases: 33 OpenAPI, 5 AsyncAPI, 30 JSON schemas, 5 capability definitions, 2 platform definitions | Ownership declarations do not prove execution |
| HTTP coverage | 166 operations discovered directly from canonical OpenAPI | Last completed hosted run qualified 9 operations |
| Composition and generation | 6 source assemblies; exact generated clients, authority projections and installed bytes | Source generation cannot qualify producer behavior |
| Dependency closure | 49 independently derived release edges and 37 installed copies | Registry-only consumers still need actual boundary witnesses |
| Consumer isolation | Exact success status/schema; request identity and scope binding on observable Inventory/Catalogue responses | Some wire responses omit scope fields; those need producer isolation evidence or a new contract release |
| Runtime packaging | Nine image and five wheel attestations; exact current release/source bytes | Vendor byte integrity and actual deployed enrollment are separate claims |
| Security proof | Missing-credential, authenticated current-authority, and cross-tenant denials are independently required | Most operations lack the complete positive/denial/state controls |
| Event boundaries | AsyncAPI address/message/payload checks plus measured installed decoders | Broker send, delivery and all actual consumers are not fully qualified |
| Native capability | Five migration methods across six modes; explicit E2 implementation outcomes and fail-closed authority | E2 does not establish native E3/E4 qualification or production write authority |

## Corrections implemented

| Finding | Severity | Correction and verification |
| --- | --- | --- |
| Schema-valid Inventory/Catalogue responses could refer to another request's record or scope | High | Bind returned application, revision, deployment, reference, endpoint, generation, migration group, tenant and site fields where the current wire exposes them. Check reference kind and environment-filtered records. Schema-valid substitution controls must fail while their corresponding positive response succeeds. |
| Extra path parameters could override the tenant in the URL while delegation used the original tenant | High | Resolve only the exact required UUID path parameters; reject missing, unexpected, reserved and non-string values before requesting delegation. |
| Catalogue buffered the entire body before enforcing its size limit | Medium | Read a bounded stream and close it on success or rejection. Share the same implementation with Inventory; test exact-limit, limit-plus-one, large, and empty streams. |
| Default JSON/YAML parsing accepted duplicate authority keys and non-JSON values | Medium | Use strict contract document reads across canonical discovery, builds, integrity, assurance admission, registry-driven attestation and aggregation. Reject duplicate keys, non-finite numbers, non-string keys, recursive YAML and implicit timestamp objects. |
| Every journey claim rebuilt and validated the entire inventory | Medium | Reuse one validated inventory inside each admission invocation. Final assessment independently reloads current canonicals. Regression tests check invocation count, fresh reads after changed bytes, malformed receipts, and unchanged proof admission. |
| The registry duplicated owner/consumer records in two editable indexes | Medium | Remove the duplicate index. Version 2 accepts one ownership catalogue and rejects a second editable index. Independent source, route, event, dependency and installed-copy discovery still detect omitted releases. |
| Assurance documentation described five claims while the gate requires six | Low | Document authentication separately from authorization. |

A local replay of the same 18 retained Planning claim records took 53.743 seconds
with an inventory rebuild per claim and 2.877 seconds with one invocation-scoped
validator (18.68× faster for that admission workload). Both accepted the same
18 records; this replay awards no new live evidence. Final aggregation remains
an independent inventory read.

Canonical published bytes remain immutable. These changes update current consumers
and tooling directly; they introduce no runtime aliases, compatibility adapters,
or historical contract copies. Git review-base data remains necessary for immutable
publication and conservative deletion/change-impact checks; it is not shipped as a
runtime fallback.

## Qualification work still required

The last completed hosted checkpoint is
[run 38886110190](https://github.com/awalker0878/multi-tenant/actions/runs/38886110190),
which tested PR merge commit `85c58c6b0bde040a637660283328bd7a7fdc5499` for source
head `0aed629fb7fb1c7846257b60add6330009df16a2`. All 48 implementation,
SQL/browser and runtime-binding jobs passed. `CI / Contract assurance` and its
dependent required gate failed: 408/1,073 claims, 27/271 consumer boundaries,
9/166 HTTP operations and 6/75 canonical releases qualified. There are 195
boundaries missing evidence. This is the measured baseline, not a claim that this
audit has already earned fresh receipts.

| Missing evidence category | Boundaries |
| --- | ---: |
| Authentication | 3 |
| Authorization | 155 |
| Consumer | 187 |
| Producer | 161 |
| Route | 5 |
| Tenant isolation | 154 |

The highest-value next implementation work is:

1. Extend actual Console-to-Inventory and Console-to-Catalogue witnesses across
   the changed operations. Retain positive wire traces and schema-valid foreign
   response controls; admit only the executed operation/consumer pair.
2. Add producer and authenticated scope/tenant denials for remaining operations,
   snapshotting all owner state around rejected writes. A route match or a 401
   cannot substitute for an authenticated isolation check.
3. Measure health routes per hosting service. The three shared health operations
   must not let one service's success qualify every declared host. The other two
   missing route claims are the worker migration method effect/observation routes.
4. Execute event publisher, broker delivery and each installed consumer. A valid
   encoder/decoder pair alone does not prove broker delivery.
5. Review operation-specific caller ownership against actual call sites. Current
   release-wide caller declarations can overstate which consumers use an operation;
   revise them only from independent runtime evidence, never to improve the score.
6. Commission deployment-owned Planning collection enrollment and the missing
   VMware NSX/AHV native qualification and receiving evidence. Keep native authority
   held until the deployment owner supplies verifiable current evidence.

Keep the strict aggregate gate and draft PR state. New unit regressions demonstrate
correctness of these fixes; live qualification requires fresh source-bound hosted
artifacts with no evidence exemptions.
