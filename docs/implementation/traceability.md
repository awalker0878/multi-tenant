# Requirement traceability

Generated from [delivery-register.yaml](delivery-register.yaml). Edit the register and run `python scripts/render_delivery_views.py` from the repository root. Do not edit this view independently.

Status meanings and review rules are in [status-model.md](status-model.md). Empty evidence fields mean no reviewed evidence has been registered; document existence is not implementation.

Requirement wording and campaigns are owned by [requirements-and-qualification.md](requirements-and-qualification.md). Contracts below link to candidate specifications, not implemented API schemas. Gate criteria are in [gates.md](gates.md).

## Requirement mapping

| Requirement | Packages | Decisions | Contract / service specifications | Campaigns | Gates |
| --- | --- | --- | --- | --- | --- |
| R01 | P00.01, P00.02, P00.03, P00.04, P00.05, P00.06, P01.01 | ADR-001, ADR-002, ADR-004, ADR-005, ADR-013, ADR-014, ADR-024 | [catalogue](../../docs/services/catalogue.md), [governance](../../docs/services/governance.md) | Q01 | G00, G01 |
| R02 | P01.01, P01.02, P01.03, P01.04, P01.05, P10.02 | ADR-003, ADR-004, ADR-005, ADR-006, ADR-008, ADR-012, ADR-024 | [README](../../docs/contracts/README.md), [examples](../../docs/contracts/examples.md) | Q01, Q09 | G01, G10 |
| R03 | P02.01, P02.02, P02.03, P02.04, P02.05, P06.01, P06.03 | ADR-009, ADR-010, ADR-018 | [governance](../../docs/services/governance.md), [lifecycle](../../docs/services/lifecycle.md) | Q01, Q03, Q04 | G02, G06 |
| R04 | P02.03, P03.05, P04.04, P05.02, P06.03, P10.03 | ADR-006, ADR-009, ADR-010 | [governance](../../docs/services/governance.md), [examples](../../docs/contracts/examples.md) | Q01, Q02, Q03, Q04, Q09 | G02, G03, G04, G05, G06, G10 |
| R05 | P03.01, P03.02, P03.03, P03.04, P03.05 | ADR-013, ADR-012 | [catalogue](../../docs/services/catalogue.md), [examples](../../docs/contracts/examples.md) | Q01 | G03 |
| R06 | P00.02, P03.01, P03.02, P03.05, P05.02 | ADR-013, ADR-004 | [catalogue](../../docs/services/catalogue.md), [planning](../../docs/services/planning.md) | Q01, Q06 | G00, G03, G05, G07 |
| R07 | P03.02, P05.02, P07.02, P07.04, P09.01, P09.04 | ADR-013, ADR-015, ADR-016 | [planning](../../docs/services/planning.md), [lifecycle](../../docs/services/lifecycle.md) | Q05, Q06, Q08 | G03, G05, G07, G09 |
| R08 | P04.01, P04.02, P04.03, P05.02, P07.01, P09.01 | ADR-011, ADR-015, ADR-018 | [inventory](../../docs/services/inventory.md), [assurance](../../docs/services/assurance.md) | Q02, Q05, Q06 | G04, G05, G07, G09 |
| R09 | P04.02, P04.03, P09.01, P09.05 | ADR-015, ADR-012 | [inventory](../../docs/services/inventory.md) | Q02, Q08 | G04, G09 |
| R10 | P04.01, P04.02, P04.03, P04.04, P04.05 | ADR-009, ADR-010, ADR-015 | [inventory](../../docs/services/inventory.md), [governance](../../docs/services/governance.md) | Q02 | G04 |
| R11 | P04.03, P05.02, P09.03 | ADR-013, ADR-016, ADR-021 | [inventory](../../docs/services/inventory.md), [lifecycle](../../docs/services/lifecycle.md) | Q02, Q03, Q08 | G04, G05, G09 |
| R12 | P05.01, P05.02, P05.05 | ADR-015, ADR-017, ADR-018 | [planning](../../docs/services/planning.md), [assurance](../../docs/services/assurance.md) | Q03 | G05 |
| R13 | P04.02, P05.01, P05.02, P06.01, P06.04, P09.05 | ADR-015, ADR-018, ADR-022 | [planning](../../docs/services/planning.md), [assurance](../../docs/services/assurance.md) | Q02, Q03, Q08 | G04, G05, G06, G09 |
| R14 | P05.04, P05.06, P06.01 | ADR-009, ADR-012, ADR-016, ADR-018 | [planning](../../docs/services/planning.md), [governance](../../docs/services/governance.md), [lifecycle](../../docs/services/lifecycle.md), [examples](../../docs/contracts/examples.md) | Q03 | G05, G06 |
| R15 | P01.03, P06.01, P06.02, P06.05 | ADR-007, ADR-008, ADR-012 | [lifecycle](../../docs/services/lifecycle.md), [examples](../../docs/contracts/examples.md) | Q04 | G01, G06 |
| R16 | P06.03, P06.05, P07.02, P07.05 | ADR-007, ADR-009, ADR-016, ADR-018 | [lifecycle](../../docs/services/lifecycle.md), [governance](../../docs/services/governance.md) | Q04, Q05 | G06, G07 |
| R17 | P05.03, P05.06, P06.03, P06.05, P07.03, P08.02 | ADR-015, ADR-016, ADR-017 | [planning](../../docs/services/planning.md), [lifecycle](../../docs/services/lifecycle.md) | Q03, Q04, Q05, Q07 | G05, G06, G07, G08 |
| R18 | P07.01, P07.02, P07.03, P07.04, P07.06 | ADR-014, ADR-015, ADR-016, ADR-018 | [lifecycle](../../docs/services/lifecycle.md), [console](../../docs/services/console.md) | Q05 | G07 |
| R19 | P03.02, P05.02, P05.04, P07.02, P07.03, P07.04 | ADR-013, ADR-014, ADR-015, ADR-016 | [catalogue](../../docs/services/catalogue.md), [planning](../../docs/services/planning.md), [lifecycle](../../docs/services/lifecycle.md) | Q05 | G03, G05, G07 |
| R20 | P05.02, P07.04, P07.06, P08.06, P09.01, P09.04 | ADR-013, ADR-015, ADR-018 | [planning](../../docs/services/planning.md), [assurance](../../docs/services/assurance.md) | Q06, Q07, Q08 | G05, G07, G08, G09 |
| R21 | P05.02, P07.03, P07.04, P08.04, P08.06 | ADR-010, ADR-015, ADR-017 | [lifecycle](../../docs/services/lifecycle.md), [planning](../../docs/services/planning.md) | Q05, Q07 | G05, G07, G08 |
| R22 | P06.02, P06.05, P08.01, P08.02, P08.03, P08.06 | ADR-014, ADR-015, ADR-017 | [lifecycle](../../docs/services/lifecycle.md), [inventory](../../docs/services/inventory.md) | Q07 | G06, G08 |
| R23 | P06.02, P06.03, P06.05, P08.03, P08.04, P08.06 | ADR-014, ADR-016, ADR-018 | [lifecycle](../../docs/services/lifecycle.md), [governance](../../docs/services/governance.md) | Q04, Q07 | G06, G08 |
| R24 | P06.02, P06.05, P08.05, P08.06 | ADR-014, ADR-017 | [lifecycle](../../docs/services/lifecycle.md) | Q04, Q07 | G06, G08 |
| R25 | P07.05, P08.06, P10.04 | ADR-009, ADR-010, ADR-021 | [lifecycle](../../docs/services/lifecycle.md), [governance](../../docs/services/governance.md), [assurance](../../docs/services/assurance.md) | Q05, Q07, Q09 | G07, G08, G10 |
| R26 | P09.01, P09.02, P09.05 | ADR-014, ADR-015, ADR-022 | [lifecycle](../../docs/services/lifecycle.md), [assurance](../../docs/services/assurance.md) | Q08 | G09 |
| R27 | P09.02, P09.04, P09.05 | ADR-014, ADR-015, ADR-022 | [planning](../../docs/services/planning.md), [lifecycle](../../docs/services/lifecycle.md), [assurance](../../docs/services/assurance.md) | Q08 | G09 |
| R28 | P09.04, P10.01 | ADR-007, ADR-017, ADR-022 | [lifecycle](../../docs/services/lifecycle.md), [planning](../../docs/services/planning.md) | Q08, Q10 | G09, G10 |
| R29 | P01.05, P01.06, P06.02, P06.05, P07.05, P10.02 | ADR-007, ADR-010, ADR-011, ADR-017, ADR-020 | [lifecycle](../../docs/services/lifecycle.md), [assurance](../../docs/services/assurance.md) | Q04, Q09 | G01, G06, G07, G10 |
| R30 | P01.06, P06.06, P07.06, P10.04 | ADR-010, ADR-011, ADR-017 | [console](../../docs/services/console.md), [lifecycle](../../docs/services/lifecycle.md), [assurance](../../docs/services/assurance.md) | Q04, Q09, Q10 | G01, G06, G07, G10 |
| R31 | P01.04, P01.06, P02.01, P06.03, P06.04, P07.01, P08.02, P09.05, P10.03 | ADR-006, ADR-009, ADR-010, ADR-011, ADR-020 | [governance](../../docs/services/governance.md), [assurance](../../docs/services/assurance.md) | Q01, Q04, Q06, Q09 | G01, G02, G06, G07, G08, G09, G10 |
| R32 | P00.05, P02.03, P05.02, P10.03 | ADR-009, ADR-010, ADR-011, ADR-020, ADR-021 | [governance](../../docs/services/governance.md), [planning](../../docs/services/planning.md), [assurance](../../docs/services/assurance.md) | Q03, Q09 | G00, G02, G05, G10 |
| R33 | P03.04, P04.05, P05.05, P06.06, P07.04, P08.04, P11.02, P11.03 | ADR-019, ADR-017 | [console](../../docs/services/console.md) | Q01, Q05, Q07, Q10 | G03, G04, G05, G06, G07, G08, G11 |
| R34 | P00.05, P04.04, P10.01 | ADR-017, ADR-020, ADR-022 | [inventory](../../docs/services/inventory.md), [lifecycle](../../docs/services/lifecycle.md), [console](../../docs/services/console.md) | Q02, Q10 | G00, G04, G10 |
| R35 | P01.03, P01.04, P10.02, P10.05, P10.06, P11.01, P11.02, P11.03, P11.04 | ADR-012, ADR-017, ADR-020, ADR-022, ADR-024 | [README](../../docs/contracts/README.md), [assurance](../../docs/services/assurance.md) | Q09, Q10 | G01, G10, G11 |
| R36 | P00.01, P00.05, P10.05, P11.05 | ADR-021 | [inventory](../../docs/services/inventory.md), [lifecycle](../../docs/services/lifecycle.md), [assurance](../../docs/services/assurance.md) | Q09 | G00, G10, G11 |

## Requirement state

| Requirement | Work | Verification | Native qualification | Operating acceptance | Evidence | Blockers |
| --- | --- | --- | --- | --- | --- | --- |
| R01 | IN_PROGRESS | IN_PROGRESS | NOT_STARTED | NOT_STARTED | EV-P00-001, EV-P00-002, EV-P00-003, EV-P00-004 | BL-P00-001, BL-P00-002 |
| R02 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R03 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R04 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R05 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R06 | IN_PROGRESS | NOT_RUN | NOT_STARTED | NOT_STARTED | — | BL-P00-001 |
| R07 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R08 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R09 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R10 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R11 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R12 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R13 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R14 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R15 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R16 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R17 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R18 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R19 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R20 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R21 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R22 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R23 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R24 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R25 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R26 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R27 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R28 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R29 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R30 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R31 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R32 | IN_PROGRESS | NOT_RUN | NOT_STARTED | NOT_STARTED | — | BL-P00-001 |
| R33 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R34 | IN_PROGRESS | NOT_RUN | NOT_STARTED | NOT_STARTED | — | BL-P00-001 |
| R35 | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | — | — |
| R36 | IN_PROGRESS | NOT_RUN | NOT_STARTED | NOT_STARTED | — | BL-P00-001 |

## Package coverage

Derived from the canonical requirement-to-package mappings. A package with no linked requirement needs review.

| Package | Requirements |
| --- | --- |
| P00.01 | R01, R36 |
| P00.02 | R01, R06 |
| P00.03 | R01 |
| P00.04 | R01 |
| P00.05 | R01, R32, R34, R36 |
| P00.06 | R01 |
| P01.01 | R01, R02 |
| P01.02 | R02 |
| P01.03 | R02, R15, R35 |
| P01.04 | R02, R31, R35 |
| P01.05 | R02, R29 |
| P01.06 | R29, R30, R31 |
| P02.01 | R03, R31 |
| P02.02 | R03 |
| P02.03 | R03, R04, R32 |
| P02.04 | R03 |
| P02.05 | R03 |
| P03.01 | R05, R06 |
| P03.02 | R05, R06, R07, R19 |
| P03.03 | R05 |
| P03.04 | R05, R33 |
| P03.05 | R04, R05, R06 |
| P04.01 | R08, R10 |
| P04.02 | R08, R09, R10, R13 |
| P04.03 | R08, R09, R10, R11 |
| P04.04 | R04, R10, R34 |
| P04.05 | R10, R33 |
| P05.01 | R12, R13 |
| P05.02 | R04, R06, R07, R08, R11, R12, R13, R19, R20, R21, R32 |
| P05.03 | R17 |
| P05.04 | R14, R19 |
| P05.05 | R12, R33 |
| P05.06 | R14, R17 |
| P06.01 | R03, R13, R14, R15 |
| P06.02 | R15, R22, R23, R24, R29 |
| P06.03 | R03, R04, R16, R17, R23, R31 |
| P06.04 | R13, R31 |
| P06.05 | R15, R16, R17, R22, R23, R24, R29 |
| P06.06 | R30, R33 |
| P07.01 | R08, R18, R31 |
| P07.02 | R07, R16, R18, R19 |
| P07.03 | R17, R18, R19, R21 |
| P07.04 | R07, R18, R19, R20, R21, R33 |
| P07.05 | R16, R25, R29 |
| P07.06 | R18, R20, R30 |
| P08.01 | R22 |
| P08.02 | R17, R22, R31 |
| P08.03 | R22, R23 |
| P08.04 | R21, R23, R33 |
| P08.05 | R24 |
| P08.06 | R20, R21, R22, R23, R24, R25 |
| P09.01 | R07, R08, R09, R20, R26 |
| P09.02 | R26, R27 |
| P09.03 | R11 |
| P09.04 | R07, R20, R27, R28 |
| P09.05 | R09, R13, R26, R27, R31 |
| P10.01 | R28, R34 |
| P10.02 | R02, R29, R35 |
| P10.03 | R04, R31, R32 |
| P10.04 | R25, R30 |
| P10.05 | R35, R36 |
| P10.06 | R35 |
| P11.01 | R35 |
| P11.02 | R33, R35 |
| P11.03 | R33, R35 |
| P11.04 | R35 |
| P11.05 | R36 |
