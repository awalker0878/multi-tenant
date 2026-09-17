from pathlib import Path
import json,html,shutil
from catalogue import ROOT,DOCS,DATA
work=Path(__file__).resolve().parent
for n in ['catalogue.py','doc_engine.py','build_architecture.py','build_engineering.py','build_implementation.py','build_runbooks.py','build_navigation.py']:
 if (work/n).exists() and (work/n).resolve() != (ROOT/'source'/n).resolve():shutil.copy2(work/n,ROOT/'source'/n)
p=ROOT/'source/catalogue.py';s=p.read_text();s=s.replace("ROOT=Path('/mnt/data/Portable_Hosting_Delivery_Kits_v1_0')","ROOT=Path(__file__).resolve().parents[1]");p.write_text(s)
# Keep build_navigation as a release-authoring utility, not a mandatory rebuild step.
roles=[('Architecture','01_Architecture','AK','AT','Architecture_Registers.xlsx','Define what is required, why, where the boundaries are and which variations are acceptable.','Eight outputs: mandate, applicability, HLD views, decisions, threat/sharing review, service strategy, native/provisioning strategy and engineering handoff.'),
('Engineering','02_Engineering','EK','ET','Engineering_Schedules.xlsx','Specify exactly how an actual site and supported stack will realize the accepted architecture.','Nine outputs: LLD, physical/BOM/port inventory, network/path schedules, compute/storage, management/services/trust, calculations, exact tuple/operation coverage, build/test design and implementation handoff.'),
('Implementation','03_Implementation','IK','IT','Implementation_Tracker.xlsx','Commission the accepted design, produce actual observations, obtain readiness decisions and hand over the service.','Ten outputs: change authority, staging, P0/P1, P2, P3, restricted qualification, initial readiness, tenant activation, as-built/evidence and continuing lifecycle.')]
for role,folder,guide,template,wb,purpose,outputs in roles:
 text=f'''# {role} delivery kit\n\n**Kit v1.0 • Frozen architecture baseline v1.4 • Proposed working material**\n\n{purpose}\n\n## Open these working materials\n\n- [{DOCS[guide][1]}]({Path(DOCS[guide][0]).name})\n- [{DOCS[template][1]}]({Path(DOCS[template][0]).name}) — tagged editable Word response fields\n- [{wb}]({wb}) — open the **Start** worksheet for instructions\n- [Delivery map](../00_Delivery_Map.docx)\n- [Frozen parent architecture](../05_Reference_v1_4/00_Reference_Architecture_v1_4.docx)\n- [Worked delivery example](../04_Shared/Worked_Delivery_Example.docx)\n\n## Expected outputs\n\n{outputs}\n\n## Working rules\n\nCreate a project-controlled copy. Fill actual owners, resources, values, support records and evidence. Teal fields and cells indicate working inputs; example-labelled material is not an allocation or approval. Word, Excel and CSV files do not synchronize automatically: designate one authoritative project record for each field and link to it from the other materials.\n\nAn accepted status requires an attributable scope-specific decision. Do not put secrets, unrestricted plan/state contents or sensitive diagnostics into this portable library. Store protected evidence in the approved repository and record references.\n\nThe site must supply exact topology, installed versions/entitlements, co-residency approval, service parameters, supported native artifacts and operating authority. No live infrastructure work or qualification has been performed by generating the kits.\n'''
 if role=='Engineering':text+='\n## Additional engineering material\n\n[Vendor realization cards](Vendor_Realization_Cards.docx) cover Nutanix, VMware/NSX, OpenStack, physical fabric/OOB and shared security/services. [KIT-TN-01](../04_Shared/KIT-TN-01_NSX_Gateway_Mode_Check.md) adds a scoped compatibility check without changing the frozen architecture.\n'
 if role=='Implementation':text+='\n## Runbooks\n\nThe `runbooks` folder contains ten site-parameterized methods. Supply exact approved commands/configuration artifacts and actual target values before execution. They are not deployable native adapters. Use the [local tools guide](../06_Tools/README.md) for offline package and saved-plan checks.\n'
 (ROOT/folder/'README.md').write_text(text,encoding='utf-8')
(ROOT/'README.md').write_text('''# Portable Hosting — Architecture, Engineering and Implementation Delivery Kits

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
''',encoding='utf-8')
(ROOT/'06_Tools/README.md').write_text('''# Read-only local checks

These utilities do not connect to infrastructure, apply configuration, allocate resources or authorize operation. They use the Python standard library.

## Package check

From the extracted root:

```console
python 06_Tools/check_package.py
```

This checks the declared release files, hashes, reference fingerprints, document hyperlink/bookmark targets, response tags and catalogue counts. Editing a project copy will deliberately invalidate release hashes. Keep the original release separate from the working project.

## Optional Terraform saved-plan metadata screen

Use only an authorized protected JSON export of an already generated saved plan. The JSON may contain secrets even when normal display output redacts them. The kit does not generate a plan, initialize a provider or execute any apply. Supply a controlled local file:

```console
python 06_Tools/review_tfplan.py protected-plan.json
```

The tool reports deletion/replacement, state-forgetting, moved addresses, unknown values, drift, deferred changes and an explicitly incomplete/errored plan when present. It never includes resource before/after values in output. Resource addresses themselves may still be sensitive. Keep both input and output protected.

Exit 0 means no selected metadata trigger, not approval. Exit 1 means explicit review triggers. Exit 2 means input is unsupported or malformed. A missing resource_changes array is not treated as evidence of an empty plan. The screen does not evaluate topology, policy, provider compatibility, privileges, current evidence or operating authority. Always use the architecture/engineering/implementation review and current actual approval.

## Local synthetic tests

```console
python -m unittest discover -s 06_Tools/tests -v
```

These exercise the offline parser and non-disclosure behaviour using fabricated non-production metadata. They do not execute the inherited infrastructure test procedures.

Source context: https://developer.hashicorp.com/terraform/cli/commands/plan . Source/API compatibility still needs review when using a newer JSON format or new actions.
''',encoding='utf-8')
(ROOT/'04_Shared/KIT-TN-01_NSX_Gateway_Mode_Check.md').write_text('''# KIT-TN-01 — Verify NSX parent-gateway mode before selecting Tier-0 VRF

**Status:** additional engineering review check; not an amendment to the frozen architecture and not a production change instruction.

The v1.4 architecture treats an isolated Tier-0 VRF as one candidate upstream realization and requires exact release/feature qualification. Broadcom KB 442835 describes a restriction when the parent Tier-0 uses active-active stateful mode. Therefore the engineering record must name the parent mode, VRF functions, Edge placement, installed releases and supported feature combination rather than accepting the words “Tier-0 VRF” as a complete design.

Review the current applicable vendor documentation and actual installed tuple. A required different mode or topology is an architecture-impacting change with service interruption, routing, stateful inspection and recovery consequences to assess. Do not reconfigure a live parent gateway to satisfy this checklist without a separate approved design/change and qualification.

**Owner:** VMware/NSX platform and network/security engineering. **Blocking point:** selecting/qualifying the affected native realization. **Record:** engineering Stack_Tuples and Operation_Coverage; LLD §8; Vendor Realization Card §3. **Actual disposition:** unresolved until the site supplies support evidence.

Official source (reviewed 16 September 2026): https://knowledge.broadcom.com/external/article/442835/cannot-add-tier0-vrf-gateway-to-a-tier0.html

[Parent architecture](../05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Vendor cards](../02_Engineering/Vendor_Realization_Cards.docx)
''',encoding='utf-8')
src='# Source register and authority\n\nFrozen v1.4 documents are the immediate architecture basis. The original uploaded handbook is historical lineage, not a reason to reintroduce its controller-centric framing or superseded topology assumptions. All new kit record formats, workplans and example delivery IDs are local proposed practices. External sources below support only the stated mechanism/context; they do not qualify an installed platform.\n\n'
for r in DATA['sources']:src+=f"## {r['id']} — {r['title']}\n\n{r['review_scope']} Reviewed {r['reviewed']}.\n\n{r['url']}\n\n"
src+='## Publishing reference\n\nMicrosoft Open XML hyperlink class documentation was used to review document-link representation. This is a publishing reference, not an infrastructure requirement.\n\nhttps://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.hyperlink?view=openxml-3.0.1\n'
(ROOT/'04_Shared/Sources_and_Lineage.md').write_text(src,encoding='utf-8')
# Machine-readable inventory linking each deliverable to actual working files.
rows=[]
for d in DATA['deliverables']:
 r=dict(d);folder={'Architecture':'01_Architecture','Engineering':'02_Engineering','Implementation':'03_Implementation'}[r['discipline']]
 r['kit_guide']=DOCS[{'Architecture':'AK','Engineering':'EK','Implementation':'IK'}[r['discipline']]][0]
 r['working_template']=DOCS[{'Architecture':'AT','Engineering':'ET','Implementation':'IT'}[r['discipline']]][0]
 r['workbook']=folder+'/'+{'Architecture':'Architecture_Registers.xlsx','Engineering':'Engineering_Schedules.xlsx','Implementation':'Implementation_Tracker.xlsx'}[r['discipline']]
 rows.append(r)
(ROOT/'04_Shared/delivery_inventory.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False))
# Static index intentionally has no application/controller logic.
parts=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Portable Hosting Delivery Kits</title><style>body{font:17px/1.55 system-ui,sans-serif;color:#21333c;max-width:1180px;margin:40px auto;padding:0 24px;background:#f7fafb}h1,h2{color:#15384a}h1{font-size:38px;line-height:1.15}a{color:#08686f}header,.card{background:white;padding:25px 30px;border:1px solid #c7d5dc;border-radius:6px;margin:22px 0}.label{color:#0b6b70;font-weight:700;letter-spacing:.08em;font-size:13px}.notice{border-left:5px solid #0b6b70;background:#eef5f7;padding:16px 22px}table{border-collapse:collapse;width:100%;font-size:15px}td,th{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #d8e1e5}th{color:#15384a}li{margin:.35em 0}code{font-size:14px}</style></head><body><header><div class="label">ARCHITECTURE → ENGINEERING → IMPLEMENTATION</div><h1>Portable Multi-Tenant Secure Hosting<br>Delivery Kits</h1><p>Kit v1.0 · 16 September 2026 · Frozen reference architecture v1.4</p><p>Architecture decides what and why. Engineering specifies the build. Implementation proves and hands over the actual service.</p><p><a href="00_Delivery_Map.docx">Open the delivery map and gates</a> · <a href="README.md">Read the working instructions</a></p></header>']
parts.append('<div class="notice"><strong>Working kit, not an approved site design.</strong> Keep this extracted folder structure intact. In each workbook, select the <strong>Start</strong> worksheet for instructions. Examples, unresolved inputs, observed evidence and authority decisions remain separate.</div>')
for role,folder,guide,template,wb,purpose,outputs in roles:
 parts.append(f'<section class="card"><h2>{role} kit</h2><p>{html.escape(purpose)}</p><p>{html.escape(outputs)}</p><ul>')
 for label,path in [('Kit guide',DOCS[guide][0]),('Editable Word response template',DOCS[template][0]),('Excel working registers / calculators',folder+'/'+wb),('Role instructions',folder+'/README.md')]:parts.append(f'<li><a href="{path}">{label}</a></li>')
 if role=='Engineering':parts.append('<li><a href="02_Engineering/Vendor_Realization_Cards.docx">Nutanix, VMware/NSX, OpenStack and shared infrastructure cards</a></li>')
 parts.append('</ul></section>')
parts.append('<section class="card"><h2>Implementation runbooks</h2><p>Ten reference methods, with 61 site-parameterized steps. Exact native artifacts and actual execution permissions are required.</p><ul>')
for p in sorted((ROOT/'03_Implementation/runbooks').glob('*.md')):parts.append(f'<li><a href="{p.relative_to(ROOT).as_posix()}">{html.escape(p.stem.replace("_"," "))}</a></li>')
parts.append('</ul></section><section class="card"><h2>Worked delivery and source context</h2><ul>')
for label,path in [('Decision → design → build → evidence example',DOCS['EX'][0]),('Extra NSX gateway-mode engineering check','04_Shared/KIT-TN-01_NSX_Gateway_Mode_Check.md'),('Sources and lineage','04_Shared/Sources_and_Lineage.md'),('Offline checks and limits','06_Tools/README.md')]:parts.append(f'<li><a href="{path}">{label}</a></li>')
parts.append('</ul><h3>Frozen v1.4 reference library</h3><ul>')
for p in sorted((ROOT/'05_Reference_v1_4').glob('*.docx')):parts.append(f'<li><a href="{p.relative_to(ROOT).as_posix()}">{html.escape(p.stem.replace("_"," "))}</a></li>')
parts.append('</ul></section><section class="card"><h2>Acceptance dependency</h2><p>G0 design, G1 foundation, G2 platform/service qualification, applicable <strong>G4 initial operational/recovery readiness</strong>, current tenant evidence and valid operating authority precede <strong>G3 production activation</strong>. Continuing G4 after activation does not replace the initial readiness.</p><p>Restricted disposable qualification is a separately authorized activity. The source test catalogues and actual result starters remain <strong>not run</strong>. No live deployment, native adapter implementation, platform qualification or authorization is claimed.</p></section></body></html>')
(ROOT/'START_HERE.html').write_text(''.join(parts),encoding='utf-8')
print('Navigation, source notes and role instructions written')
