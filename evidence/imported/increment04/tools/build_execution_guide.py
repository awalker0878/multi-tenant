#!/usr/bin/env python3
"""Build the Increment04 Word guide from current local result records.

Requires python-docx for publishing only. Does not run provider code or invent
qualification results. The rendered document must be visually reviewed separately.
"""
from pathlib import Path
import json
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT

ROOT=Path(__file__).resolve().parents[1]
LOCAL=json.loads((ROOT/'quality/local_validation.json').read_text())
PACKET=json.loads((ROOT/'quality/local_packet_lab.json').read_text())
REFS=json.loads((ROOT/'sources/increment04_references.json').read_text())
DNS=json.loads((ROOT/'quality/local_dns_transactions.json').read_text())
NATIVE=json.loads((ROOT/'quality/local_native_readback.json').read_text())
DOC=Document()
sec=DOC.sections[0];sec.page_width=Inches(8.5);sec.page_height=Inches(11)
sec.top_margin=Inches(.6);sec.bottom_margin=Inches(.6);sec.left_margin=Inches(.7);sec.right_margin=Inches(.7)
sec.header_distance=Inches(.25);sec.footer_distance=Inches(.25)
styles=DOC.styles
for name in ('Normal','Body Text'):
 styles[name].font.name='Calibri';styles[name].font.size=Pt(10.5)
 styles[name].paragraph_format.space_after=Pt(7)
 styles[name].paragraph_format.line_spacing=1.1
for name,size in [('Title',30),('Heading 1',20),('Heading 2',12.5)]:
 styles[name].font.name='Calibri';styles[name].font.size=Pt(size);styles[name].font.color.rgb=RGBColor.from_string('153F50')
 styles[name].paragraph_format.space_after=Pt(10)
styles['Caption'].font.size=Pt(9)
if 'Code' not in styles:styles.add_style('Code',1)
styles['Code'].font.name='Liberation Mono';styles['Code'].font.size=Pt(8.5)
styles['Code'].paragraph_format.line_spacing=1.0;styles['Code'].paragraph_format.space_after=Pt(4)
header=sec.header.paragraphs[0];header.text='PORTABLE SECURE HOSTING  /  IMPLEMENTATION INCREMENT 04'
header.style='Caption'
footer=sec.footer.paragraphs[0];footer.style='Caption';footer.text='Candidate native source • Local fixture evidence only   |   '
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
DOC.core_properties.title='Portable Secure Hosting — Implementation Increment 04'
DOC.core_properties.subject='Native selected-state observation and interrupted-change recovery'
DOC.core_properties.author=''
DOC.core_properties.keywords='Infrastructure; Native implementation; Terraform; Qualification; Increment04'


def p(text,style=None):return DOC.add_paragraph(text,style)
def h(text):return DOC.add_heading(text,2)
def link(label,target,paragraph=None):
 paragraph=paragraph or DOC.add_paragraph()
 node=OxmlElement('w:hyperlink')
 if target.startswith('#'):node.set(qn('w:anchor'),target[1:])
 else:node.set(qn('r:id'),paragraph.part.relate_to(target,RT.HYPERLINK,is_external=True))
 run=OxmlElement('w:r');prop=OxmlElement('w:rPr');color=OxmlElement('w:color');color.set(qn('w:val'),'00717D');prop.append(color)
 under=OxmlElement('w:u');under.set(qn('w:val'),'single');prop.append(under);run.append(prop);text=OxmlElement('w:t');text.text=label;run.append(text);node.append(run);paragraph._p.append(node)
 return paragraph

def table(headings,rows,widths=None):
 t=DOC.add_table(rows=1,cols=len(headings));t.autofit=False
 widths=widths or [7.1/len(headings)]*len(headings)
 for c,w,text in zip(t.rows[0].cells,widths,headings):c.width=Inches(w);c.text=text
 repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
 for row in rows:
  cells=t.add_row().cells
  for c,w,text in zip(cells,widths,row):c.width=Inches(w);c.text=str(text)
 for ri,row in enumerate(t.rows):
  trpr=row._tr.get_or_add_trPr();trpr.append(OxmlElement('w:cantSplit'))
  for cell in row.cells:
   tcpr=cell._tc.get_or_add_tcPr();shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'153F50' if ri==0 else 'EEF4F6' if ri%2 else 'FFFFFF');tcpr.append(shade)
   margins=OxmlElement('w:tcMar')
   for side in ('top','bottom','left','right'):
    v=OxmlElement('w:'+side);v.set(qn('w:w'),'80');v.set(qn('w:type'),'dxa');margins.append(v)
   tcpr.append(margins)
   for par in cell.paragraphs:
    par.paragraph_format.space_after=Pt(3);par.paragraph_format.line_spacing=1.0
    for run in par.runs:
     run.font.size=Pt(9.5)
     if ri==0:run.bold=True;run.font.color.rgb=RGBColor(255,255,255)
 return t


def page(number,title):
 if number>1:DOC.add_page_break()
 par=DOC.add_heading(title,1)
 bm=OxmlElement('w:bookmarkStart');bm.set(qn('w:id'),str(number));bm.set(qn('w:name'),f'chapter_{number}');par._p.insert(0,bm)
 end=OxmlElement('w:bookmarkEnd');end.set(qn('w:id'),str(number));par._p.append(end)
 if number>1:link('Contents and release status','#chapter_1').style='Caption'


page(1,'Implementation Increment 04')
p('Native readback and interrupted-change recovery','Subtitle')
p('17 September 2026 • Candidate native integrations • Executed local HTTPS and packet evidence')
h('Read the actual platform state before deciding how to recover')
p('This increment implements exact-resource NSX and Nutanix readers and an offline recovery reviewer. The readers separate accepted configuration, current native status and task completion. The reviewer checks whether the observations and externally controlled recovery records belong to the same current change. Neither component mutates infrastructure or issues operating authorization.')
table(['Delivered','Evidence boundary'],[
 ('NSX Local Manager object and intent-status reads','Selected configuration and enforcing-system status; not every host’s effective rules'),
 ('Nutanix VPC/subnet and single-task reads','Networking/prism v4.3 candidate profile; no composite tasks or native changes'),
 ('Interrupted-change triage and local HTTPS fault campaign','Actual local code/protocol tests; simulated fence/quarantine records'),
 ('Ten existing Terraform module/root pairs retained','Engine/plugins still unavailable; native validation and qualification not run')],[3.4,3.7])
p('No user or vendor infrastructure was contacted. The toolchain download retry failed at container DNS resolution. Existing DNS and routed IPv4/mTLS tests were rerun separately; they do not qualify these native readers.')
h('Guide navigation')
for n,title in [(2,'Infrastructure ownership and readback coverage'),(3,'NSX configuration and realization'),(4,'Nutanix resources and asynchronous tasks'),(5,'Interrupted-change decision procedure'),(6,'Transport, credentials and protected evidence'),(7,'Local execution and observed results'),(8,'Native commissioning and stopping conditions'),(9,'Primary native-interface sources'),(10,'Release integrity and remaining work')]:
 link(f'{n}. {title}',f'#chapter_{n}')

page(2,'Infrastructure ownership and readback coverage')
p('A native change can complete after its runner loses the reply. A successful configuration GET can precede policy realization. A completed task can coexist with the wrong resource state. Readback therefore means observing the selected native configuration and progress after the change, while retaining the actual owner, scope and version of the original operation.')
table(['Owner / boundary','Accepted input','Observation or hold'],[
 ('Platform resource owner','Exact native IDs, current expected fields and supported API profile','Compare selected configuration; no object creation or adoption'),
 ('Network/security owner','Domain/gateway/policy and current expected realization version','Match the declared status span; preserve independent quarantine'),
 ('Change and execution owner','Original operation, plan, generation, task IDs and writer status','Pending tasks and uncertain writers stop ordinary recovery'),
 ('Incident authority','Current containment and release authority','An observation cannot release an active incident restriction'),
 ('Operations / data owner','Current data/retention obligations and accepted operating conditions','Preserve resources and data until a separately authorized decision')],[1.6,2.8,2.7])
h('Exact selected resources, not a discovery service')
p('The NSX profile reads segments, Tier-1 gateways, static routes, groups and gateway/security policies through Local Manager paths. The Nutanix profile reads VPCs and subnets plus one known task through networking/prism v4.3. The existing Neutron reader is retained independently. No reader claims complete inventory or all-platform lifecycle coverage.')
p('Portable tenant/domain labels are bound to native identities by an accepted engineering record. They do not create native RBAC or prove that the selected records cover every relevant dependency. A native tenantId is not automatically the architecture’s customer tenant label.')
h('Architecture remains the authority')
link('Reference architecture and provisioning strategy','reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx')
link('Worked infrastructure design and acceptance','reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx')
link('Increment04 architecture-to-code mapping','sources/increment04_traceability.csv')
p('These tools fit the existing implementation work packages and evidence handoffs. They do not require a new hosting controller, resource API, scheduler, message bus or authorization application. Existing change and inventory systems can hold the records.')

page(3,'NSX configuration and realization')
p('The selected Local Manager pattern reads the exact object, reads its intent status, and reads the object again. Configuration identity, selected values and _revision must remain consistent around the status query. Two identical completed samples are required. A native write or status-refresh POST is never issued. [N1–N4]')
table(['Observation','Required match / reason for a hold'],[
 ('Configuration identity','Exact path, id, resource type and nonnegative native revision; no similar-name substitution'),
 ('Policy and rules','Category, sequence, statefulness; rule identity/order/action, direction/family, logging/enabled state, membership and negation, scope, referenced/inline services and profiles'),
 ('Intent version','Separately recorded expected intent_version. It is not assumed equal to the configuration _revision.'),
 ('Publication and aggregate status','Publication REALIZED and consolidated SUCCESS; pending/error/unknown remain distinct'),
 ('Enforcing-system coverage','Exactly the accepted enforcement-point paths, each reporting SUCCESS; no missing, extra or duplicate span'),
 ('Stable sampling','A config revision change around status collection is uncertain; do not combine two different revisions into one success')],[1.85,5.25])
h('Rules are not normalized into apparent equivalence')
p('The implementation preserves order and exact list membership. Expected rule sequences must be unique. Source/destination exclusion flags, inline services and profile lists are explicit; changed negation or extra service entries cannot be hidden behind an unchanged group/service name. Missing fields remain unknown rather than silently defaulted. [N3]')
h('What a matching status does not prove')
p('The API’s enforcement-point status refers to an enforcing system/site, not proof that every ESXi or Edge node has the intended rules. This profile does not request each transport node’s enforced state, inspect the entire global rule hierarchy, resolve every group’s actual membership or run a native packet trace. Those remain separate qualification and operating observations. [N1]')
p('Only the Local Manager /infra path profile is implemented. Global Manager and project-root variants are not translated automatically. The consulted latest documentation identifies NSX 9.1.1.0; this does not establish compatibility with an installed release or with the retained provider version. An unsupported status/resource combination remains a hold, not a fallback.')
link('Detailed native procedure and selected-field coverage','docs/NATIVE_READBACK.md')

page(4,'Nutanix resources and asynchronous tasks')
p('The selected networking/prism v4.3 profile observes a recorded task, the exact VPC/subnet resources, and the task again. It requires a stable completed task and matching selected resource values with exact accepted strong ETags. Task success alone cannot satisfy resource readback. [U1–U5]')
table(['Object / signal','Checks implemented'],[
 ('VPC','extId, object type, native tenantId, name/type, external-subnet membership, externally routable prefixes and ETag'),
 ('Subnet','extId, object type, native tenantId, name/type, VPC reference, external flag, IP configuration and ETag'),
 ('Task binding','Exact opaque task ID, operation, time interval and affected resource IDs. IDs are encoded; callback URLs are not followed.'),
 ('Task completeness','Zero subtasks and no batch summary; full exact affected-entity count/list. Limited or unresolved scope is unknown.'),
 ('Completion','SUCCEEDED with valid completion time and no diagnostics needing review; later resource differences remain differences.'),
 ('Failure and pending','QUEUED/RUNNING/CANCELING are pending. FAILED/CANCELED requires partial-effect review, not automatic rollback.')],[1.65,5.45])
h('Missing metadata is not an empty or successful result')
p('Some native fields can be omitted by an API representation. This strict profile does not silently treat an absent external-subnet list as empty or an absent status as success. Missing expected fields/ETag, weak ETag, foreign identity, incomplete entities or unknown states keep the outcome unresolved. An engineered site profile must establish safe normalization before relaxing these checks.')
p('The task is deliberately limited to one known, fully enumerated operation. If its returned entity/subtask list is incomplete, the implementation does not recursively discover and cancel work. Preserve the native task identifier at submission; a missing identifier cannot be repaired by guessing a UUID.')
h('Installed capability is still separate')
p('The wire profile is derived from the networking and prism Go SDK v4.3.1 interfaces and models. The new Python reader does not execute that SDK and does not negotiate another API. VMs, Flow policies, route resources, composite tasks and native repair are outside this increment. Native tenant identity, strong ETag behavior and actual read permissions must be accepted on the chosen platform. [U1–U6]')
link('Disabled Nutanix input example','examples/nutanix_observation.json.example')

page(5,'Interrupted-change decision procedure')
p('An interrupted run first needs actual writer control and preserved data. A stopped runner does not prove that asynchronous native work stopped. Do not replay a create, cancel a task, unlock state, import a resource or restore an old state file merely because the original reply was lost.')
table(['Condition','Reviewer outcome / required owner action'],[
 ('Active or unknown containment','KEEP_INCIDENT_CONTAINMENT / HOLD_CONTAINMENT_UNKNOWN; ordinary convergence cannot release it'),
 ('Runner or writer not controlled','HOLD_WRITER_NOT_FENCED; obtain actual scoped, current fencing evidence'),
 ('New generation supersedes the attempt','HOLD_SUPERSEDED_CHANGE; compare against the current accepted change'),
 ('Quarantine not independently verified','HOLD_QUARANTINE_NOT_VERIFIED; matching config is not safe connectivity'),
 ('Native task/publication pending','WAIT_FOR_NATIVE_TASK; keep the original operation identity and do not resend'),
 ('Task failed/canceled or config differs','INSPECT_PARTIAL_FAILURE / RECONCILE_DIVERGENCE; assess actual resources and data'),
 ('Missing/stale/contradictory observation','HOLD_NATIVE_UNCERTAINTY / HOLD_INVALID_EVIDENCE; resolve or recollect'),
 ('All implemented record checks pass','READY_FOR_OPERATOR_RECOVERY_REVIEW; still no apply, delete or activation permission')],[2.4,4.7])
h('Three independently controlled inputs')
p('The offline reviewer binds the accepted manifest, readback report and change/recovery context. It checks target/scope/operation, digests, history consistency, freshness, generation and the recorded fence/quarantine/containment state. It recomputes the result instead of trusting a final label. The default freshness cap of 300 seconds is a local tool value, not government policy.')
p('Every result retains may_apply=false, may_delete=false and may_activate=false. The tool does not authenticate approval signatures or prove that a real writer was fenced. Evidence references and JSON hashes provide record linkage, not native control. Actual fencing, resource/data ownership and the next mutation decision remain with their authorities.')
link('Complete interrupted-change procedure','docs/INTERRUPTED_CHANGE_RECOVERY.md')
link('Deliberately incomplete recovery context example','examples/recovery_context.json.example')

page(6,'Transport, credentials and protected evidence')
p('The new clients perform only enumerated HTTPS GETs. The caller supplies an exact expected origin; the transport accepts only generated resource/status paths. It does not follow redirects or response links, use environment proxies, discover resources, refresh credentials or issue native mutations.')
table(['Protection','Implemented behavior / remaining prerequisite'],[
 ('Server trust and credentials','Verified certificate/hostname, strict SSL context, no ambient TLS keylogging. Scoped Basic credentials injected through NSXT_* or NUTANIX_* environment variables.'),
 ('Response validation','HTTP 200 JSON object only; duplicate keys/nonfinite numbers, malformed framing, unsupported encoding, oversized/truncated bodies and ambiguous ETags are rejected.'),
 ('Bounded collection','Default 20-resource limit, 3 rounds, 5-second socket timeout, 60-second cooperative budget, 400-GET ceiling and 2 MiB body limit. These are tool bounds, not service guarantees.'),
 ('Timeout limitation','Response reads use remaining budget on the live TLS socket. OS hostname resolution is not forcibly interrupted; native execution needs an external deadline and accepted DNS.'),
 ('Private journal','New exclusive non-symlink file, mode 0600; incomplete record before contact, flush/fsync on write. Parent directory and durable evidence custody remain external.'),
 ('Data minimization','Safe error codes and selected-state hashes; no raw credential/service exception text echoed. Hashes are not signatures or immutable retention.')],[1.65,5.45])
h('No-contact checks and explicit read-only contact')
p('python tools/nsx_observe.py examples/nsx_observation.json.example','Code')
p('python tools/nutanix_observe.py examples/nutanix_observation.json.example','Code')
p('python tools/nsx_observe.py /secure/nsx-expected.json \\\n  --read-authorized-target --expected-origin https://nsx.site.invalid \\\n  --ca-file /secure/approved-ca.pem --output /secure/new-readback.json','Code')
p('The .invalid endpoint is intentionally unusable. Actual reads require an enabled accepted manifest, matching real origin and injected credentials. NSXT_USERNAME/NSXT_PASSWORD and NUTANIX_USERNAME/NUTANIX_PASSWORD are variable names, not values to paste in chat or source. No-contact validation and matching readback can both exit 0; neither authorizes a change.')

page(7,'Local execution and observed results')
p('The new fixture uses actual loopback TLS and HTTP GET exchanges with scripted published response shapes. It is not a vendor emulator. Task responses, fencing and quarantine records are controlled fault fixtures; actual native task execution, RBAC, fencing and HA were not exercised.')
table(['Check','Current executed result / scope'],[
 ('Python unit/source/local protocol suite',f"{LOCAL['unit_and_source_tests']['run']} run; zero failures, errors or skips. Includes the new reader/recovery regressions."),
 ('Native-readback fault campaign',f"{NATIVE['passed']} passed; {NATIVE['failed']} failed. End-to-end local observation plus offline recovery triage, not additional unique unit coverage."),
 ('Existing DNS wire campaign',f"{DNS['passed']} passed. TCP/TSIG authority fixture; subset of unit suite, not production DNS qualification."),
 ('Existing IPv4 packet/mTLS campaign',f"{PACKET['passed']} passed. Fixed 17-namespace fixture; original namespace configuration unchanged."),
 ('Offline dual-family route checks','80 passed. Model calculations, not native or routed IPv6 execution.'),
 ('Terraform and native qualification','BLOCKED / NOT RUN. No actual plugin schema, lockfile, mocked-plan pass or vendor-side read claimed.')],[2.4,4.7])
h('Faults that change the recovery decision')
p('The campaign exercises delayed task/publication completion, NSX configuration changing around status reads, stale intent versions, incomplete enforcing-system span, a failed Nutanix task with an existing resource, HTTP 404, wrong native tenant, changed ETag and incomplete affected entities. Unverified writer fencing, active containment and superseding generations remain holds even after selected-state match.')
p('Additional regressions cover untrusted TLS, redirects, proxy/keylog inheritance, malformed/ambiguous data, absent optional fields, rule order/negation/inline services, slow body delivery, exclusive journal creation, stale/future observations and tampered history. Passing local fixtures proves the implemented handling of those cases, not truthfulness or completeness of a real management plane.')
link('Current local regression record','quality/local_validation.json')
link('Native-readback campaign observations','quality/local_native_readback.json')
link('Retained routed packet and identity campaign','quality/local_packet_lab.json')
link('Actual Terraform blocker and download attempt','quality/toolchain_access.json')

page(8,'Native commissioning and stopping conditions')
table(['Hold point','Required implementation work before proceeding'],[
 ('1. Toolchain','Verified Terraform and trusted plugins; actual source/schema/mock-plan checks. Python/source tests do not waive this gate.'),
 ('2. Target and authority','Select installed product/API/provider combination, disposable scope, exact origin/CA and read-only principal. No customer target was supplied or contacted in this release.'),
 ('3. Expected state','Accept native IDs, selected fields and real version/ETag/task/intent tokens independently. A response copied into its own expected record is not verification.'),
 ('4. Read and preserve','Run no-contact validation, then explicit scoped GETs with a fresh private output. No repair action is hidden in a reader.'),
 ('5. Interrupted work','Establish actual writer fencing and quarantine; retain containment, data and old evidence. Review current native progress and selected configuration before proposing another mutation.'),
 ('6. Independent verification','Assess actual packet paths, rule precedence, host placement, data access, DNS/identity/protection and failure behavior under the accepted profile.'),
 ('7. Service activation','Required initial operational/recovery readiness and applicable authorization precede production. No new tool sets service readiness or releases quarantine.')],[1.55,5.55])
h('Local commands after extraction')
for line in ['python tools/check_release.py','python tools/check_local.py','python lab/run_readback_lab.py --execute','python lab/run_dns_lab.py --execute','python lab/run_namespace_lab.py --execute','python tools/check_package.py']:
 p(line,'Code')
p('Run release integrity first: test commands intentionally refresh quality files. The local labs accept only their bounded fixtures. Runtime readers use the standard library; fixture certificates use the retained tested cryptography dependency. Existing DNS and packet tests need the documented additional libraries and Linux namespace tools.')
link('Commissioning sequence','docs/COMMISSIONING.md')
link('Native operation and integration backlog','sources/implementation_backlog.csv')

page(9,'Primary native-interface sources'),(10,'Release integrity and remaining work')
p('Immediate baseline: Implementation Increment03. All 139 frozen reference files and 50 Terraform source files are preserved. The source manifest records the baseline; the new code and documents are separately identified. The existing architecture, resource owners and required initial-readiness gates have not been replaced by a software-controller design.')
h('Primary native-interface sources')
for ids in [('N1',),('N2','N3','N4'),('U1','U2'),('U3','U4','U5'),('U6',),('T4',)]:
 selected=[r for r in REFS if r['id'] in ids]
 par=p(' / '.join(r['id'] for r in selected)+' — '+selected[0]['title']);par.paragraph_format.space_after=Pt(2)
 for run in par.runs:run.bold=True;run.font.size=Pt(10)
 desc=' '.join(r['locator']+'.' for r in selected)
 p(desc+' '+selected[0]['review_scope']+'. Reviewed 17 September 2026.','Caption')
 for r in selected:
  link(r['id']+' official source',r['url']).style='Caption'
page(10,'Release integrity and remaining work')
h('Remaining native scope')
p('Qualify the selected readback profiles against real API behavior, expected-field omission, identity, task scope and RBAC before relying on them. Add supported VM/Flow/route and composite-task readback deliberately; do not claim the current readers cover them. Actual writer fencing, state reconciliation and forward repair remain native-owner work.')
p('The next infrastructure dependencies remain the selected EC/SE firewall and installed platform combination, real attachment/policy/inspection/HA implementation, IPAM and production service integrations, native IPv6 and actual operating qualification. No native ALLOW policy, provider switch, unverified state import or automatic activation is introduced.')
h('Scope the next accepted native increment')
table(['Required owner input','What it enables'],[
 ('Installed NSX or Nutanix tuple, native read principal and exact disposable target','Validate the candidate profile against real field omission, token and status behavior.'),
 ('Actual EC/SE firewall and attachment implementation','Build the domain and service contexts, policy/inspection, interfaces, return routes and HA.'),
 ('Native execution and fencing mechanism','Track and control outstanding tasks, reconcile state and design an authorized forward repair.'),
 ('Shared-service and recovery acceptance','Integrate actual IPAM, DNS, identity, keys, storage and backup with the required operating evidence.')],[2.75,4.35])
h('Release handling')
p('Verify release hashes immediately after extraction. The hash manifest detects byte differences; it does not authenticate the publisher or approver. Local tests intentionally refresh their quality reports. Do not replace a historical source record with a new successful result or interpret a previous release’s report as evidence for changed code.')
p('The package contains source and documentation only: no provider cache, native state, saved live plan, private key or generated fixture credential. Re-extraction verification is recorded separately. Frozen reference documents and workbooks are preserved, not newly rendered, recalculated or authorized.')
link('Complete source review register','sources/increment04_references.json')
link('Increment03 source fingerprints','sources/increment03_manifest.json')
p('Public documentation supports the stated interface shapes. Version pins and local response fixtures do not establish installed compatibility, organizational approval or full security assurance. No third-party SDK, private key, provider binary or font file is shipped.','Caption')
DOC.save(ROOT/'Implementation_Execution_Guide.docx')
print(ROOT/'Implementation_Execution_Guide.docx')
