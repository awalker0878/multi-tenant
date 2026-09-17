# Portable Hosting — Architecture, Engineering and Implementation Delivery Kits

**Kit v1.0 • 16 September 2026 • Architecture baseline: frozen v1.4**

Open `START_HERE.html` for the linked index, or `00_Delivery_Map.docx` for the workflow and acceptance gates. Keep the extracted folder structure intact. The kit release number is independent of the architecture version; the eight reference Word documents are preserved, not rewritten.

## Three connected kits

| Kit | Primary working output | Start |
|---|---|---|
| Architecture | HLD, boundaries, decisions, applicability and engineering handoff | `01_Architecture/README.md` |
| Engineering | LLD, actual resource/path schedules, supported tuple, calculations and build/test release | `02_Engineering/README.md` |
| Implementation | Reviewed method, actual build/test evidence, initial readiness, controlled activation and operations | `03_Implementation/README.md` |

The bundle includes nine new Word documents, three working Excel workbooks, ten runbooks, a shared delivery catalogue, a complete copied 194-requirement reference index, and the frozen eight-document architecture library. The Word forms use editable tagged response controls. In each workbook, open the **Start** worksheet. Reference examples and actual working records are separate.

## Handoffs and gates

Architecture supplies accepted scope, decisions, sharing/service constraints and requirements. Engineering supplies actual topology, native support, values, calculations, approved artifacts, build and evidence plans. Implementation records actual native results and obtains the appropriate acceptance decisions.

G0/G1/G2 and the applicable **G4 initial operational/recovery readiness** plus current tests and valid operating authority precede **G3 production activation**. Later continuing G4 exercises do not replace the initial proof. A separately authorized disposable qualification fixture may run before G2; it cannot authorize production.

## Using the kit on a project

Assign the actual architecture, engineering, implementation, service, data and security owners. Complete the HLD and applicability register first, then resolve the LLD and exact platform/service tuple. Use one native stack plus all required shared infrastructure for the first scoped qualification; repeat outcomes on the next stack for separate portability evidence. A simultaneous split-stack service needs its own composite design.

Copy forms into the controlled project location and preserve stable record IDs across diagrams, schedules, methods and evidence. Do not maintain conflicting working copies across teams. CSV catalogues are reference snapshots; Word, Excel and CSV do not automatically synchronize. Do not enter actual credentials into these files.

## What is and is not supplied

Supplied: reusable guides, response templates, reference schedules, calculators, stage methods, review and handover records, local metadata checks, sources and traceability. All additional workflow structures are proposed kit practices; baseline-derived statements cite RA/WD and external checks use K references.

Not supplied or asserted: actual site decisions, approved bills of materials, installed compatibility, executable native Terraform adapters, production configuration commands, credentials, live platform test results or authorization. Runbooks become executable only after the site supplies approved native artifacts, exact targets and scope-specific authority. Unknown values remain blockers instead of being filled from product defaults.

## Validation and maintenance

`07_Quality` records local document/workbook/tool checks. These do not establish infrastructure qualification. `06_Tools/check_package.py` verifies the package read-only. `06_Tools/review_tfplan.py` is an optional metadata-only screen for a protected JSON saved plan; it neither calls providers nor authorizes apply. Test procedures remain not run.

The 80 CT procedures and 12 realization addenda are historical reference specifications recovered from the v1.2 traceability package as named in the later library. The 12 W14 assertions are from v1.4. Applicability and actual assertion coverage require target-specific review; their presence is not evidence that every inherited procedure is applicable or repaired.

The `source` directory includes document and workbook construction source. Run rebuilds only in a separate copy and re-render/review before release. The publishing environment uses python-docx and the workbook builder uses artifact_tool; a separate installation of those dependencies is required. Exact binary reproduction across renderers is not asserted.
