"""Generate navigation and reference registers for the v1.1 development release.

This does not update project workbooks, native infrastructure or acceptance status.
"""
from pathlib import Path
import csv
import html
import json
import re
import shutil
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '04_Shared/development'
SPECS = json.loads((ROOT/'08_Development_Source/documents.json').read_text())
SOURCES = json.loads((ROOT/'08_Development_Source/sources.json').read_text())


def csv_write(path, rows):
    if not rows:
        raise ValueError(f'No rows for {path}')
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)


def destination(code, section):
    return SPECS[code]['path'] + f'#{code}_{section:02d}'

# Baseline review observations are development opportunities, not verified deployment defects.
# Fields identify the exact documentation treatment and the remaining implementation work.
D = [
('Service envelope', 'AK §2; RA §2', 'The guide identifies service requirement groups; a completed offer still needs choices and exclusions.', 'SDP',1,'AK-01; AK-02','Architecture/service owner','G0', 'An internal-service decision table separates ordinary VM service from exposure and higher-assurance extensions.', 'Adopt actual categories, responsibilities, service classes and exclusions.', 'Accepted service envelope and named owners.'),
('Sharing scope', 'AK §4; RA §7', 'Layer-specific sharing questions need an explicit option and consequence record.', 'SDP',2,'AK-04; AK-05','Architecture/security authority','G0', 'Develops dedicated versus shared host, control, storage, edge and service choices without treating dedication as a checkbox.', 'Resolve actual domain compatibility, residual risk and ancillary dependencies.', 'Approved sharing matrix and applicable supporting analysis.'),
('Boundary decision', 'AK §7; RA §29', 'Alternatives should be reasoned before native components are selected.', 'SDP',3,'AK-03; AK-04; AK-07','Architecture/network/security owners','G0', 'DEV-ADR-01 compares explicit edge and qualified native/distributed alternatives and rejects unrestricted transit.', 'Adopt a topology and identify actual qualified enforcement locations.', 'Decision record, related views and assigned engineering constraints.'),
('Consumer dependencies', 'AK §2; EK §5', 'Service dependency names do not identify the actual caller, privilege or data path.', 'SDP',4,'AK-05; AK-06; EK-05','Service/identity/data owners','G0; G2', 'Separates guest, host, backup and administrative clients with explicit entitlement and recovery dependencies.', 'Name the real callers, endpoints, support/location and authority scope.', 'Interface records and accepted provider/consumer responsibilities.'),
('Capacity and service cost', 'AK §5; RA §26', 'Capacity-on-demand needs a decision model that does not confuse installed capacity with offered capacity.', 'SDP',5,'AK-06; EK-06','Capacity/service owner','G0; G2', 'Develops inventory, entitlement, reservation, cost allocation and expansion reasoning without invented prices.', 'Supply actual service demand, measured capacities, lead time and approved rates if used.', 'Accepted service envelope, capacity model and measurement rules.'),
('Architecture handoff', 'AK §8; DEL §2', 'A generic handoff checklist benefits from a directly completable decision record.', 'SDP',6,'AK-08; EK-01','Architecture and engineering leads','G0', 'Adds six editable handoff response controls linked to the existing HLD record.', 'Complete the actual design, owner and unresolved-decision record.', 'Receiver-accepted architecture release; no blocking ambiguity.'),
('Isolation units', 'EK §3; WD §4', 'Domain attachments, service attachments and hardware counts must not be interchanged.', 'NBD',1,'EK-03; EK-06','Network/security engineering','G1; G2', 'Accounts separately for four domain and two service handoffs and logical EC/SE units.', 'Map logical units to supported physical/virtual contexts and spare capacity.', 'Actual interface and context inventory with supported limits.'),
('Forward and reply routes', 'EK §3; WD §6', 'The path schedule needs explicit end-to-end reasoning as well as prefixes.', 'NBD',2,'EK-03; EK-09','Network/security engineering','G2', 'Works F14-01 through four IPv4 route observations, stateful reply and rejected alternative forwarding.', 'Replace example allocations and inspect actual native routes, rules and session behaviour.', 'Observed forward/reply trace and forbidden-path evidence.'),
('Service return routing', 'EK §5; WD §7', 'Shared-service reachability alone does not demonstrate originating-tenant return routing.', 'NBD',3,'EK-03; EK-05','Network/shared-service owners','G2', 'Works DNS forward and origin-specific return routing through EC-01 and SE-01.', 'Prove the selected service/gateway implementation supports the intended reply path and no transit.', 'Service-side routes, tenant attribution and access/denial observations.'),
('Family and MTU budgets', 'EK §6; NET §5', 'A generic MTU value hides address-family and encapsulation assumptions.', 'NBD',4,'EK-03; EK-06','Network/platform engineering','G1; G2', 'Defines family-specific qualification and explicit 1550/1570-byte basic VXLAN outer-IP examples.', 'Supply real tunnel/options/tags, vendor MTU convention and surviving-path limits.', 'Reviewed packet budget plus actual PMTU and protocol observations.'),
('Fabric configuration ownership', 'EK §2; VC §5', 'Fabric, optional EVPN and tenant overlay state have separate ownership and failure scopes.', 'NBD',5,'EK-02; EK-03; EK-07','Foundation/network owner','G1', 'Develops provider-owned transport, route authority, multihoming and configuration boundaries.', 'Supply device tuple, peer/port map, actual native artifacts and safe maintenance procedures.', 'Accepted foundation inventory/configuration and failure record.'),
('Interface acceptance', 'EK §5; PROV §1', 'A producer receipt must contain enough information for a consumer to use the interface safely.', 'NBD',6,'EK-05; EK-09','Producing and consuming owners','G1; G2', 'Adds six editable interface-control fields for identity, policy, capacity, ownership and evidence.', 'Populate actual endpoints, protocols, limits and handoff acknowledgements.', 'Signed or otherwise attributable accepted interface record.'),
('Survivor bottleneck', 'EK §6; QUAL §3', 'One free capacity dimension cannot offset an exhausted security-path bottleneck.', 'NBD',7,'EK-06; EK-08','Capacity/edge owner','G2', 'Shows a local 8 minus 1.5 minus 5.5 Gbit/s budget and rejection of 1.2 Gbit/s additional demand.', 'Measure sustainable inspected capacity and account for all commitments/reserves once.', 'Actual per-bottleneck admission and failure-load evidence.'),
('Native lifecycle ownership', 'EK §7; VC §1', 'Provider availability is not complete lifecycle support for each resource family.', 'PBS',1,'EK-07; EK-08; IK-03','Platform/automation/service owners','G1; G2', 'Develops installer/API/Terraform and service ownership across P0–P6.', 'Confirm observe/create/update/adopt/replace/delete and unknown-outcome handling per actual resource.', 'Operation coverage and single-writer release record.'),
('Nutanix build specification', 'VC §2; RA §16', 'The realization card needs foundation and tenant-resource build detail.', 'PBS',2,'EK-04; EK-07; IK-04','Nutanix platform owner','G2', 'PBS §§2–3 develop control, AOS/AHV sharing, isolated VPC handoffs, deny-first build and lifecycle checks.', 'Select supported hardware/AOS/Prism/Flow/API/provider tuple and exact native artifacts.', 'Installed tuple, platform receipts and actual boundary/data/recovery observations.'),
('VMware/NSX build specification', 'VC §3; RA §17', 'Distributed/service routing and gateway HA choices need separate proof.', 'PBS',4,'EK-04; EK-07; IK-04','VMware/network/security owners','G2', 'PBS §§4–5 develop transport, Tier-0/Tier-1 handoffs, policy and gateway-mode compatibility checks.', 'Resolve actual HA, VRF/isolated alternative, advertisement and storage/placement support.', 'Supported topology and observed native/edge paths and failover.'),
('OpenStack build specification', 'VC §4; RA §18', 'Distribution/backend ownership and additive policy need an enforceable native design.', 'PBS',6,'EK-04; EK-07; IK-04','OpenStack platform/network owners','G2', 'PBS §§6–7 develop controller/backend/placement foundations and provider-owned baseline mutation.', 'Select actual distribution/backend/extensions/API policy and observe enforcement after lifecycle changes.', 'Native role/policy, path, scheduling and storage receipts.'),
('Shared-service producer handoff', 'VC §6; EK §5', 'Selected hosting providers do not own every identity, backup, edge or addressing dependency.', 'PBS',8,'EK-05; EK-07; IK-05','Shared-service owners','G2', 'Provides producer/consumer handoff facts and protects against broad state/credential sharing.', 'Populate actual endpoint/use limits, acceptance and scoped credentials under each owner.', 'Accepted service handoffs and target-side authority evidence.'),
('Build release quality', 'EK §8; IT §1', 'The release must identify real native artifacts, not just a generic supported-operation statement.', 'PBS',9,'EK-08; EK-09; IK-01','Engineering/deployment leads','G2', 'Adds six build-release fields and operation-level stop/recovery conditions.', 'Supply reviewed site configuration, scripts/modules, exact versions and actual change scope.', 'Accepted engineering release with a complete MOP and no guessed dependency.'),
('Campaign applicability and fixture', 'IK §6; QUAL §5', 'A procedure catalogue needs a scoped campaign and adequate temporary resources.', 'QCP',1,'IK-06; EK-08','Assurance lead','Restricted fixture; G2', 'QCP §§1–2 separate first-stack, comparison and exit claims and account for sequential/simultaneous probe demand.', 'Authorize target scope, families, shared dependencies, intrusive-test safety and actual fixture capacity.', 'Approved campaign with explicit applicable assertions and resource reservation.'),
('Meaningful observations', 'IK §6; IT §4', 'Expected outcomes need independent healthy controls and artifacts, not inferred passes.', 'QCP',3,'IK-06; IK-09','Assurance and technical owners','G2', 'Twelve Q11 cards in §§3–5 elaborate existing CT observations for paths, authority, data, failures and restore.', 'Execute authorized observations and record actual results separately from expected values.', 'Attributable evidence for each applicable assertion and defect/retest record.'),
('Evidence and scoped acceptance', 'QUAL §5; IK §7', 'A status or test count does not prove coverage, freshness or operating authority.', 'QCP',6,'IK-07; IK-08; IK-09','Assurance/service acceptance owner','G2; G4 initial; G3', 'QCP §§6–8 develop evidence review, cross-stack claim boundaries and six acceptance response fields.', 'Resolve blocked/failed/NA evidence, actual reviewer and exact accepted service scope.', 'Current scoped qualification and separate readiness/activation decisions.'),
('Dependency operations and maintenance', 'IK §8; IK §9', 'Failure plans must distinguish established service, new changes and recovery authority.', 'OPS',1,'IK-07; IK-10','Operations/platform/service owners','G4 initial; G4 continuing', 'OPS §§1–3 develop service-level operation, dependency loss and interrupted-change decisions.', 'Confirm target-specific cache, native-task, state, credential and containment behaviour.', 'Exercised operating playbook and actual support/recovery owners.'),
('Recovery, transition and retained data', 'IK §9; SVC §6', 'Recovery and migration need critical-path, writer and retained-copy decisions, not only VM restart.', 'OPS',4,'AK-06; IK-07; IK-09; IK-10','Recovery/data/operations owners','G4 initial; G3; G4 continuing', 'OPS §§4–8 develop ordered recovery, local 140/160-minute examples, writer transition and six handover fields.', 'Measure actual recovery/consistency, approve cutover/failback and reconcile every retained-copy/key obligation.', 'Accepted recovery evidence, operating handover and disposal/retention receipts.'),
]


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    csv_write(OUT/'source_reviews.csv', SOURCES)
    register=[]
    for i,row in enumerate(D,1):
        topic,basis,obs,code,sec,outputs,owner,gate,treatment,remaining,evidence=row
        register.append(dict(id=f'DD-{i:02d}',topic=topic,baseline_locator=basis,development_observation=obs,
           treatment=treatment,document_code=code,section=sec,document_path=SPECS[code]['path'],
           bookmark=f'{code}_{sec:02d}',role_outputs=outputs,responsible_role=owner,blocking_gate=gate,
           remaining_implementation_work=remaining,closure_evidence=evidence,
           documentation_status='Developed reference treatment',implementation_status='Open; no target execution or approval',
           actual_owner='',actual_evidence=''))
    csv_write(OUT/'development_register.csv',register)
    (OUT/'development_register.json').write_text(json.dumps(register,indent=2,ensure_ascii=False)+'\n')

    documents=[]
    for code,s in SPECS.items():
        for num,sec in enumerate(s['sections'],1):
            documents.append(dict(document_code=code,title=s['title'],document_path=s['path'],section=num,
                section_title=sec['title'],bookmark=f'{code}_{num:02d}',
                baseline_and_related_sections='; '.join(f'{c} §{n}' for c,n in sec.get('refs',[])),
                status='Proposed document development; not accepted site engineering'))
    csv_write(OUT/'document_section_index.csv',documents)

    cards=[]
    for secnum in [3,4,5]:
        for block in SPECS['QCP']['sections'][secnum-1]['blocks']:
            if block['kind']!='table': continue
            for row in block['rows']:
                label,*extra=row[0].split('\n')
                card_id,title=label.split(': ',1)
                cards.append(dict(id=card_id,title=title,existing_test_ids='; '.join(re.findall(r'CT-\d{3}',row[0])),
                    procedure_and_control=row[1],expected_result_and_artifacts=row[2],document_path=SPECS['QCP']['path'],
                    bookmark=f'QCP_{secnum:02d}',execution_status='not-run',actual_target='',observed_result='',
                    evidence_reference='',reviewer='',scope_note='Elaboration of inherited procedures, not a new control or executed result.'))
    csv_write(OUT/'qualification_observation_cards.csv',cards)

    handoffs=[]
    for block in SPECS['PBS']['sections'][7]['blocks']:
        if block['kind']=='table':
            for i,row in enumerate(block['rows'],1):
                handoffs.append(dict(id=f'DH-{i:02d}',producer_scope=row[0],handoff_content=row[1],consumer_check=row[2],
                    document_path=SPECS['PBS']['path'],bookmark='PBS_08',actual_producer='',actual_consumer='',actual_evidence='',
                    status='Reference handoff; actual acceptance not supplied'))
    csv_write(OUT/'service_handoff_development.csv',handoffs)

    examples={
        'status':'Local planning examples; not site allocations, benchmarks or approved targets',
        'fixture':{'source':'WD §11; EK §6; QCP §2','permanent_endpoints':4,'vcpus_each':2,'memory_gib_each':4,
                   'virtual_disk_gib_each':80,'sequential_probes':1,'simultaneous_probes':4,
                   'sequential_peak':{'vcpus':10,'memory_gib':20,'virtual_disk_gib':400},
                   'simultaneous_peak':{'vcpus':16,'memory_gib':32,'virtual_disk_gib':640},
                   'exclusions':'Provider/management/security/services, replicas, copies, rebuild and failure reserves are additional.'},
        'mtu':{'source':'D06; NBD §4','inner_ip_bytes':1500,'inner_ethernet_bytes':14,'vxlan_bytes':8,'udp_bytes':8,
               'outer_ipv4_bytes':20,'outer_ipv6_bytes':40,'outer_ipv4_packet_bytes':1550,'outer_ipv6_packet_bytes':1570,
               'exclusions':'No inner tags, IP options, outer extension headers, encryption or nested tunnels; outer link framing additional.'},
        'edge_capacity':{'source':'Local NBD §7 proposal','unit':'Gbit/s','surviving_capacity':'8','reserve':'1.5',
                         'existing_commitment':'5.5','additional_request':'1.2','available':'1.0','margin_after_request':'-0.2',
                         'illustrative_disposition':'Does not fit; exclude or increase qualified capacity, never bypass enforcement.'},
        'recovery':{'source':'Local OPS §5 proposal','unit':'minutes','detect':10,'decide':5,'bootstrap':25,'network':20,
                    'storage':40,'restore':35,'validate':20,'cutover':5,'target':180,'parallel_elapsed':140,
                    'serial_elapsed':160,'parallel_margin':40,'serial_margin':20,
                    'assumption':'Network and storage can run in parallel only when personnel, systems and dependencies permit.'},
        'rpo':{'source':'Local OPS §5 proposal','service_loss':'12:00','recoverable_consistency_point':'11:45',
               'job_finished':'11:55','data_age_minutes':15,'note':'Job completion time is not the accepted data consistency point.'}}
    (OUT/'engineering_examples.json').write_text(json.dumps(examples,indent=2)+'\n')

    # Save original root navigation only once, separately from active navigation.
    for name in ['README.md','START_HERE.html']:
        historical=ROOT/'07_Quality/prior_v1_0'/('ROOT_'+name)
        if not historical.exists(): shutil.copy2(ROOT/name,historical)

    md=['# Portable Hosting Delivery Kits — v1.1','',
        '**Infrastructure architecture → detailed engineering → controlled implementation → accepted operations.**','',
        'Open [the document index](START_HERE.html), then [Delivery Map and Acceptance Gates](00_Delivery_Map.docx). Extract the complete archive and keep its folder structure. Word links identify a target document and section; application security settings may prompt before opening a local file.','',
        '## Developed in this release','',
        'This release adds five substantive specifications and replaces the delivery map. It preserves the eight v1.4 parent documents, eight other v1.0 role/template/example documents, all three workbooks and the inherited requirement/test records without byte changes. Retained files keep their own version labels.','']
    for code,s in SPECS.items():
        if code!='DEL':md.append(f'- **[{code} — {s["title"]}]({s["path"]})**: {s["subtitle"]}')
    md += ['', '## Use the working records','',
       'Complete the original HLD, LLD and MOP/test/handover templates and workbooks for the actual site. The new specifications supply worked reasoning and 30 additional editable response fields; they do not grant approval or replace the project record.', '',
       '- [Development register](04_Shared/development/development_register.csv): 24 documented treatments, parent locators, output IDs, owners, gates and remaining implementation evidence.',
       '- [Section index](04_Shared/development/document_section_index.csv): exact destinations for all 46 developed sections.',
       '- [Qualification observation cards](04_Shared/development/qualification_observation_cards.csv): twelve Q11 cards elaborate existing CT procedures; every actual result remains not-run.',
       '- [Shared-service handoff record](04_Shared/development/service_handoff_development.csv): producer facts and consumer checks, with actual parties/evidence blank.',
       '- [Engineering examples](04_Shared/development/engineering_examples.json): explicit arithmetic and assumptions for fixture demand, MTU, survivor capacity and recovery timing.',
       '- [Source review register](04_Shared/development/source_reviews.csv): eight freshly reviewed public mechanism references, scope and limitations.', '',
       '## Preserve authority and status','',
       'The frozen architecture is not amended by a proposed supplement. Actual architecture variations need their existing approval process. Gate identifiers are not chronological: applicable initial G4 operational/recovery readiness precedes G3 production activation. Restricted non-production fixtures need separate permission and can produce qualification evidence without claiming production readiness.', '',
       'Site allocations, equipment/firmware/product/API/provider combinations, native commands/modules, supported configuration, measured service values, real test artifacts and authorization remain open implementation work. Documentation addresses are not actual IPAM allocations. No live test, recovery performance, production build or authorization is claimed.', '',
       '## Local checks and rebuild','',
       'Current publishing/integrity results are in [07_Quality/v1_1](07_Quality/v1_1/README.md). Historical v1.0 reports are retained in 07_Quality/prior_v1_0 and do not validate this release. Workbooks are copied unchanged; no fresh spreadsheet calculation or formula validation is asserted.', '',
       'Use [08_Development_Source/README.md](08_Development_Source/README.md) for the current document build. The retained source directory and 06_Tools/check_package.py are the original v1.0 builders/checks; do not use them to overwrite this developed release. The optional original plan-metadata reviewer is unchanged, offline and not an approval engine.', '',
       '```text',
       'python 08_Development_Source/author_content.py',
       'python 08_Development_Source/build_documents.py',
       'python 08_Development_Source/build_registers.py',
       'python 08_Development_Source/validate_release.py --root .',
       '```', '',
       'After editing or rebuilding, render and visually inspect affected Word documents, update the review record and regenerate the release manifest. A code or content edit invalidates the old publishing fingerprints.']
    (ROOT/'README.md').write_text('\n'.join(md)+'\n')

    def a(path,label):return f'<a href="{html.escape(path,quote=True)}">{html.escape(label)}</a>'
    rows=''.join(f'<tr><td>{c}</td><td>{a(s["path"],s["title"])}</td><td>{html.escape(s["subtitle"])}</td></tr>' for c,s in SPECS.items())
    groups={
      'Architecture working kit': ['01_Architecture/Architecture_Kit.docx','01_Architecture/HLD_and_Architecture_Review_Template.docx','01_Architecture/Architecture_Registers.xlsx'],
      'Engineering working kit':['02_Engineering/Engineering_Kit.docx','02_Engineering/LLD_and_Engineering_Review_Template.docx','02_Engineering/Vendor_Realization_Cards.docx','02_Engineering/Engineering_Schedules.xlsx'],
      'Implementation working kit':['03_Implementation/Implementation_Kit.docx','03_Implementation/MOP_Test_and_Handover_Template.docx','03_Implementation/Implementation_Tracker.xlsx','04_Shared/Worked_Delivery_Example.docx'],
      'Reference architecture v1.4':[p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'05_Reference_v1_4').glob('*.docx'))],
      'Reference registers and source':[p.relative_to(ROOT).as_posix() for p in sorted(OUT.glob('*.csv'))]+['04_Shared/development/engineering_examples.json','04_Shared/development/DEVELOPMENT_NOTES.md','07_Quality/v1_1/README.md','08_Development_Source/README.md']}
    sections=''.join('<h2>'+html.escape(title)+'</h2><ul>'+''.join('<li>'+a(path,Path(path).stem.replace('_',' '))+'</li>' for path in paths)+'</ul>' for title,paths in groups.items())
    (ROOT/'START_HERE.html').write_text('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Portable Hosting Delivery Kits v1.1</title><style>body{font:17px/1.55 system-ui,sans-serif;margin:2rem auto;max-width:1150px;padding:0 1.2rem;color:#21333c}h1,h2{color:#15384a}a{color:#0b6b70}table{border-collapse:collapse;width:100%;font-size:.95rem}th,td{padding:.8rem;text-align:left;vertical-align:top;border-bottom:1px solid #c8d7dc}th{background:#15384a;color:white}.notice{padding:1rem;border-left:5px solid #0b6b70;background:#eef5f7}li{margin:.3rem 0}footer{margin-top:3rem;font-size:.9rem}</style></head><body>
<h1>Portable Hosting Delivery Kits · v1.1</h1><p>Architecture decisions, buildable engineering and accountable implementation. Parent architecture v1.4 remains unchanged.</p>
<p class="notice">Extract the complete package and keep its folders together. Use the Delivery Map first. Examples, expected observations and document checks are not site approvals or deployed evidence.</p>
<h2>Developed document family</h2><table><thead><tr><th>Code</th><th>Word document</th><th>Purpose</th></tr></thead><tbody>'''+rows+'</tbody></table>'+sections+'''<footer>New documents and delivery map: 17 September 2026. Retained role material keeps v1.0 labels; the frozen architecture keeps v1.4 labels. Complete native configurations, actual parameters, live qualification and authorization separately.</footer></body></html>''')

    (OUT/'DEVELOPMENT_NOTES.md').write_text('''# Development release v1.1

This increment develops infrastructure decisions and methods. It does not change the frozen architecture or treat software/API schemas as the primary design.

## Treatment and remaining work

The [24-entry development register](development_register.csv) links reviewed v1.0 guide/card sections to new detailed treatments, stable AK/EK/IK outputs and remaining implementation evidence. These are documentation-development observations, not findings against a deployed platform. A populated treatment is not a closed site issue.

The [twelve Q11 cards](qualification_observation_cards.csv) elaborate existing CT procedures. No live result is supplied. A campaign must still choose actual scope, support tuple, endpoint/control health, appropriate safety envelope, observations, artifacts and reviewers.

The [engineering examples](engineering_examples.json) distinguish parent fixture values from new local arithmetic. Requested guest disks are not physical usable storage; simple VXLAN header arithmetic is not a universal product MTU; local recovery timing is not a service guarantee.

## Version and precedence

The current root Delivery Map replaces its v1.0 navigation role and preserves DEL_01–DEL_06 anchors for existing links. Five new companions add direct links back to the frozen reference and original role templates. The original parent, eight other role/template/example Word files, three workbooks, ten Markdown runbooks and inherited requirements/verification CSVs are byte-preserved. They retain their labels and scope.

D01–D08 are public mechanism sources reviewed for this increment. They do not select installed products or recertify earlier source dates. New record structures, method refinements and worked examples are local proposals. Source applicability and actual engineering decisions remain accountable project work.

The complete original file fingerprints are recorded in [baseline_fingerprints.json](baseline_fingerprints.json). The original delivery map, root navigation and prior validation are retained under 07_Quality/prior_v1_0 as historical snapshots; relative links inside that relocated historical snapshot are not active release navigation.

## Working practice

Choose one actual project record set in the existing workbooks/change system. Use the new editable response blocks only where they help complete a decision; do not create independent conflicting copies. Record actual owners and evidence before acceptance. The current document section index and development CSVs are reference/navigation snapshots, not a custom approval application.
''')
    print(f'Wrote {len(register)} development records, {len(documents)} section records, {len(cards)} observation cards and {len(handoffs)} handoffs.')

if __name__=='__main__':
    build()
