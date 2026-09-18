# W14 worked-design assertions

Original fields are rendered below without rewriting their procedure, scope or not-run status. These are not newly executed results. [Family index](verification-families.md).

[Original records](../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/registers/v1_4_verification_assertions.csv)

<a id="W14-01"></a>
## W14-01

**assertion:** W14-01 / routing completeness

**observation:** Every domain, edge, service next hop and return path matches the approved schedule.

**mapped_procedures_and_status:** CT-003, CT-009, CT-023, CT-024 / NOT RUN

Related baseline procedures: [CT-003](test-specifications.md#CT-003) · [CT-009](test-specifications.md#CT-009) · [CT-023](test-specifications.md#CT-023) · [CT-024](test-specifications.md#CT-024)

<a id="W14-02"></a>
## W14-02

**assertion:** W14-02 / service isolation

**observation:** Only named service endpoints and authorized resource scope are reachable; router/admin and other tenant targets deny.

**mapped_procedures_and_status:** CT-004, CT-008, CT-037 / NOT RUN

Related baseline procedures: [CT-004](test-specifications.md#CT-004) · [CT-008](test-specifications.md#CT-008) · [CT-037](test-specifications.md#CT-037)

<a id="W14-03"></a>
## W14-03

**assertion:** W14-03 / mandatory policy authority

**observation:** Tenant roles cannot attach a permissive group, disable port security or create an alternative native path.

**mapped_procedures_and_status:** CT-019, CT-020, CT-022, CT-066 / NOT RUN

Related baseline procedures: [CT-019](test-specifications.md#CT-019) · [CT-020](test-specifications.md#CT-020) · [CT-022](test-specifications.md#CT-022) · [CT-066](test-specifications.md#CT-066)

<a id="W14-04"></a>
## W14-04

**assertion:** W14-04 / family completeness

**observation:** Each offered address family has working allocation, routes, service replies, local controls and recovery.

**mapped_procedures_and_status:** CT-002, CT-031, CT-032 / NOT RUN

Related baseline procedures: [CT-002](test-specifications.md#CT-002) · [CT-031](test-specifications.md#CT-031) · [CT-032](test-specifications.md#CT-032)

<a id="W14-05"></a>
## W14-05

**assertion:** W14-05 / DNS completeness

**observation:** UDP, direct TCP and truncation/fallback work only against approved resolvers.

**mapped_procedures_and_status:** CT-008 plus explicit protocol observations / NOT RUN

Related baseline procedures: [CT-008](test-specifications.md#CT-008)

<a id="W14-06"></a>
## W14-06

**assertion:** W14-06 / intra-domain fixture

**observation:** Temporary probe verifies same-host and cross-host controls where that placement is approved.

**mapped_procedures_and_status:** CT-021, CT-035 / NOT RUN

Related baseline procedures: [CT-021](test-specifications.md#CT-021) · [CT-035](test-specifications.md#CT-035)

<a id="W14-07"></a>
## W14-07

**assertion:** W14-07 / admission accounting

**observation:** Compute, data, context, service and edge commitments fit the same accepted failure basis.

**mapped_procedures_and_status:** CT-039, CT-056, CT-074 / NOT RUN

Related baseline procedures: [CT-039](test-specifications.md#CT-039) · [CT-056](test-specifications.md#CT-056) · [CT-074](test-specifications.md#CT-074)

<a id="W14-08"></a>
## W14-08

**assertion:** W14-08 / lost executor

**observation:** Accepted native tasks and side effects are discovered; no duplicate allocation or competing writer appears.

**mapped_procedures_and_status:** CT-044, CT-045, CT-046 / NOT RUN

Related baseline procedures: [CT-044](test-specifications.md#CT-044) · [CT-045](test-specifications.md#CT-045) · [CT-046](test-specifications.md#CT-046)

<a id="W14-09"></a>
## W14-09

**assertion:** W14-09 / activation dependencies

**observation:** Production activation rejects missing applicable operating or promised recovery readiness.

**mapped_procedures_and_status:** CT-062, CT-069 plus G3/G4 review / NOT RUN

Related baseline procedures: [CT-062](test-specifications.md#CT-062) · [CT-069](test-specifications.md#CT-069)

<a id="W14-10"></a>
## W14-10

**assertion:** W14-10 / shared-service failure

**observation:** Permitted and denied paths retain the selected policy and declared service behavior during approved failure.

**mapped_procedures_and_status:** CT-011, CT-012, CT-024, CT-050 / NOT RUN

Related baseline procedures: [CT-011](test-specifications.md#CT-011) · [CT-012](test-specifications.md#CT-012) · [CT-024](test-specifications.md#CT-024) · [CT-050](test-specifications.md#CT-050)

<a id="W14-11"></a>
## W14-11

**assertion:** W14-11 / retained recovery

**observation:** Required copy, catalogue and key access survive live WSD retirement; unauthorized destruction denies.

**mapped_procedures_and_status:** CT-051, CT-052, CT-053, CT-078 / NOT RUN

Related baseline procedures: [CT-051](test-specifications.md#CT-051) · [CT-052](test-specifications.md#CT-052) · [CT-053](test-specifications.md#CT-053) · [CT-078](test-specifications.md#CT-078)

<a id="W14-12"></a>
## W14-12

**assertion:** W14-12 / second-stack outcome

**observation:** Repeat the declared environment and representative data recovery on a second eligible stack.

**mapped_procedures_and_status:** CT-016, CT-060, CT-073 / NOT RUN

Related baseline procedures: [CT-016](test-specifications.md#CT-016) · [CT-060](test-specifications.md#CT-060) · [CT-073](test-specifications.md#CT-073)
