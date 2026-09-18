# Portable Hosting Delivery Kits — v1.1

**Infrastructure architecture → detailed engineering → controlled implementation → accepted operations.**

Open [the document index](START_HERE.html), then [Delivery Map and Acceptance Gates](00_Delivery_Map.docx). Extract the complete archive and keep its folder structure. Word links identify a target document and section; application security settings may prompt before opening a local file.

## Developed in this release

This release adds five substantive specifications and replaces the delivery map. It preserves the eight v1.4 parent documents, eight other v1.0 role/template/example documents, all three workbooks and the inherited requirement/test records without byte changes. Retained files keep their own version labels.

- **[SDP — Service Design and Architecture Decisions](01_Architecture/Service_Design_and_Decision_Development.docx)**: Develop a service offer that engineering can translate into a bounded infrastructure design.
- **[NBD — Network, Boundary and Shared-Service Detailed Engineering](02_Engineering/Network_and_Boundary_Detailed_Engineering.docx)**: Connect addressing, forwarding, policy, return paths and failure behaviour in one buildable design.
- **[PBS — Platform Engineering and Build Specifications](02_Engineering/Platform_Engineering_and_Build_Specifications.docx)**: Assign native resource ownership, dependencies, build outputs and acceptance for each vendor stack.
- **[QCP — Qualification Campaign and Evidence Procedures](03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx)**: Turn requirements into healthy controls, meaningful observations and accountable acceptance.
- **[OPS — Operations, Recovery and Transition Playbook](03_Implementation/Operations_Recovery_and_Transition_Playbook.docx)**: Operate the actual service envelope, recover dependencies, and retire without losing data or authority.

## Use the working records

Complete the original HLD, LLD and MOP/test/handover templates and workbooks for the actual site. The new specifications supply worked reasoning and 30 additional editable response fields; they do not grant approval or replace the project record.

- [Development register](04_Shared/development/development_register.csv): 24 documented treatments, parent locators, output IDs, owners, gates and remaining implementation evidence.
- [Section index](04_Shared/development/document_section_index.csv): exact destinations for all 46 developed sections.
- [Qualification observation cards](04_Shared/development/qualification_observation_cards.csv): twelve Q11 cards elaborate existing CT procedures; every actual result remains not-run.
- [Shared-service handoff record](04_Shared/development/service_handoff_development.csv): producer facts and consumer checks, with actual parties/evidence blank.
- [Engineering examples](04_Shared/development/engineering_examples.json): explicit arithmetic and assumptions for fixture demand, MTU, survivor capacity and recovery timing.
- [Source review register](04_Shared/development/source_reviews.csv): eight freshly reviewed public mechanism references, scope and limitations.

## Preserve authority and status

The frozen architecture is not amended by a proposed supplement. Actual architecture variations need their existing approval process. Gate identifiers are not chronological: applicable initial G4 operational/recovery readiness precedes G3 production activation. Restricted non-production fixtures need separate permission and can produce qualification evidence without claiming production readiness.

Site allocations, equipment/firmware/product/API/provider combinations, native commands/modules, supported configuration, measured service values, real test artifacts and authorization remain open implementation work. Documentation addresses are not actual IPAM allocations. No live test, recovery performance, production build or authorization is claimed.

## Local checks and rebuild

Current publishing/integrity results are in [07_Quality/v1_1](07_Quality/v1_1/README.md). Historical v1.0 reports are retained in 07_Quality/prior_v1_0 and do not validate this release. Workbooks are copied unchanged; no fresh spreadsheet calculation or formula validation is asserted.

Use [08_Development_Source/README.md](08_Development_Source/README.md) for the current document build. The retained source directory and 06_Tools/check_package.py are the original v1.0 builders/checks; do not use them to overwrite this developed release. The optional original plan-metadata reviewer is unchanged, offline and not an approval engine.

```text
python 08_Development_Source/author_content.py
python 08_Development_Source/build_documents.py
python 08_Development_Source/build_registers.py
python 08_Development_Source/validate_release.py --root .
```

After editing or rebuilding, render and visually inspect affected Word documents, update the review record and regenerate the release manifest. A code or content edit invalidates the old publishing fingerprints.
