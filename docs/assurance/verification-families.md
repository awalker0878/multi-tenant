# Verification-family selection index

A procedure ID is not an executed result. CT, RA, W14 and Q11 overlap deliberately; do not sum their counts as unique assurance coverage. All retained execution states below are unexecuted. Actual test records require version, target, preconditions, healthy controls, observations, evidence and reviewer.

| Family | Retained entries | Purpose and applicability | Read |
|---|---:|---|---|
| CT | 80 | Baseline requirements; select by service, architecture and lifecycle stage | [Full specifications](test-specifications.md) |
| RA | 12 | Native realization elaborations of named CTs; selected platform/backend and change scope | [Full addenda](realization-addenda.md) |
| W14 | 12 | Connected internal reference design; fixture-specific architecture assertions | [Worked assertions](../solutions/internal-protected-workload/13-verification-assertions-and-actual-evidence.md) |
| Q11 | 12 | Operational observation/control cards elaborating existing test IDs | [Campaign cards](qualification-campaign/3-observe-network-paths-and-boundary-enforcement.md) |

## Explicit supplemental mappings

| ID | Source / existing test references | Selection / status |
|---|---|---|
| [RA-01](realization-addenda.md#RA-01) | CT-003, CT-009, CT-023, CT-025 | Selected native realization; not-run |
| [RA-02](realization-addenda.md#RA-02) | CT-003, CT-024, CT-080 | Selected native realization; not-run |
| [RA-03](realization-addenda.md#RA-03) | CT-023, CT-024, CT-031 | Selected native realization; not-run |
| [RA-04](realization-addenda.md#RA-04) | CT-017, CT-021, CT-022, CT-066 | Selected native realization; not-run |
| [RA-05](realization-addenda.md#RA-05) | CT-032, CT-033, CT-034 | Selected native realization; not-run |
| [RA-06](realization-addenda.md#RA-06) | CT-026, CT-027, CT-055 | Selected native realization; not-run |
| [RA-07](realization-addenda.md#RA-07) | CT-019, CT-043, CT-044, CT-045 | Selected native realization; not-run |
| [RA-08](realization-addenda.md#RA-08) | CT-035, CT-054, CT-060, CT-076 | Selected native realization; not-run |
| [RA-09](realization-addenda.md#RA-09) | CT-044, CT-048, CT-070 | Selected native realization; not-run |
| [RA-10](realization-addenda.md#RA-10) | CT-006, CT-007, CT-045, CT-069, CT-077 | Selected native realization; not-run |
| [RA-11](realization-addenda.md#RA-11) | CT-026, CT-035, CT-037, CT-078 | Selected native realization; not-run |
| [RA-12](realization-addenda.md#RA-12) | CT-056, CT-071, CT-072, CT-074 | Selected native realization; not-run |
| Q11-01 | CT-003, CT-007, CT-024 | approved path and reply; not-run |
| Q11-02 | CT-001, CT-002 | tenant isolation; not-run |
| Q11-03 | CT-021, CT-022 | same-domain policy; not-run |
| Q11-04 | CT-008, CT-023, CT-024 | shared-service return; not-run |
| Q11-05 | CT-019, CT-020, CT-022, CT-066 | mandatory mutation authority; not-run |
| Q11-06 | CT-037, CT-078 | data attachment and copy scope; not-run |
| Q11-07 | CT-028, CT-038, CT-079 | identity and key lifecycle; not-run |
| Q11-08 | CT-008, CT-030, CT-031, CT-032 | service protocols and MTU; not-run |
| Q11-09 | CT-012, CT-024, CT-034 | edge or link loss; not-run |
| Q11-10 | CT-011, CT-027, CT-038, CT-050, CT-055 | dependency loss; not-run |
| Q11-11 | CT-045, CT-046, CT-048 | uncertain provisioning outcome; not-run |
| Q11-12 | CT-052, CT-053, CT-054, CT-060 | isolated restore and cutover; not-run |

[Original W14 assertion register](../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/registers/v1_4_verification_assertions.csv) · [Original Q11 observation register](../../reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/development/qualification_observation_cards.csv)

## Acceptance boundary

A mandatory assertion that is blocked, not run or unjustifiably not applicable cannot pass a gate. First-stack acceptance does not wait for already-qualified multiple stacks; cross-stack outcome comparison and actual data/service exit are later separate claims. Reuse evidence only when target generation, topology, versions and dependency conditions remain valid.

[Assertion-to-owner allocation](../implementation/assertion-allocation.md) · [Historical finding dispositions](historical-dispositions.md)
