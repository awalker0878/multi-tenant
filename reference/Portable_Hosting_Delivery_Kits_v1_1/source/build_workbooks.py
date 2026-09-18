"""Run in Python with artifact_tool available. Builds working XLSX registers; no infrastructure changes."""
from pathlib import Path
import json,re,math
from artifact_tool import Workbook, SpreadsheetFile
root=Path(__file__).resolve().parents[1]
data=json.loads((root/"source/kit_catalogue.json").read_text())
import re, math
NAVY="#15384A"; TEAL="#0B6B70"; PALE="#EEF5F7"; EDIT="#EAF6F4"; INK="#21333C"
workbooks={}
sheet_meta={}
def col(n):
    s=""
    while n:
        n,r=divmod(n-1,26);s=chr(65+r)+s
    return s
def clean(v):
    if isinstance(v,(dict,list)):v=json.dumps(v,ensure_ascii=False)
    if isinstance(v,str) and v[:1] in ["=","+","@"]:v="'"+v
    return v
def grid(wb, name, title, note, headers, rows, widths=None, editable=None, status=None, row_height=44):
    sh=wb.worksheets.add(name)
    nc=len(headers);nr=max(1,len(rows));last=col(nc)
    sh.get_range(f"A1:{last}1").merge()
    sh.get_range("A1").values=[[title]]
    sh.get_range(f"A1:{last}1").format={"fill":NAVY,"font":{"bold":True,"color":"#FFFFFF","size":16},"row_height":30}
    sh.get_range(f"A2:{last}3").merge();sh.get_range("A2").values=[[note]]
    sh.get_range(f"A2:{last}3").format={"wrap_text":True,"font":{"color":INK,"size":10},"row_height":20,"vertical_alignment":"center"}
    sh.get_range(f"A5:{last}5").values=[headers]
    if rows:sh.get_range(f"A6:{last}{5+len(rows)}").values=[[clean(x) for x in row] for row in rows]
    sh.get_range(f"A5:{last}{5+nr}").format={"font":{"name":"Calibri","size":10,"color":INK},"wrap_text":True,"vertical_alignment":"top","row_height":row_height}
    sh.tables.add(f"A5:{last}{5+nr}",True,"T_"+re.sub(r"[^A-Za-z0-9]","",name))
    sh.get_range(f"A5:{last}5").format={"fill":NAVY,"font":{"bold":True,"color":"#FFFFFF"},"row_height":32,"wrap_text":True}
    for j,w in enumerate(widths or [22]*nc,1):sh.get_range(f"{col(j)}1:{col(j)}{5+nr}").format.column_width=w
    for j in editable or []:sh.get_range(f"{col(j)}6:{col(j)}{5+nr}").format.fill=EDIT
    for j,vals in (status or {}).items():
        rg=sh.get_range(f"{col(j)}6:{col(j)}{5+nr}")
        rg.data_validation={"rule":{"type":"list","values":vals}}
        rg.conditional_formats.add_custom(f'={col(j)}6="Blocked"',{"fill":"#FDE7D9"})
        rg.conditional_formats.add_custom(f'={col(j)}6="Failed"',{"fill":"#FDE7D9"})
    sh.freeze_panes.freeze_rows(5)
    sheet_meta[id(wb),name]=(nc,5+nr)
    return sh
STAT=["Not started","In progress","Blocked","Ready for review","Accepted","Not applicable"]
wb=Workbook.create();workbooks["Architecture"]=wb
a_del=[x for x in data["deliverables"] if x["discipline"]=="Architecture"]
sh=grid(wb,"Deliverables","Architecture delivery register","WORKING RECORD • Proposed kit practice. Accepted status requires a separate attributable decision; workbook entries do not grant authority.",
["ID","Deliverable","Owner role","Actual owner","Gate","Status","Acceptance evidence","Decision reference","Baseline"],
[[x['id'],x['title'],x['owner_role'],"",x['gate'],"Not started",x['acceptance'],"",x['baseline']] for x in a_del],
[12,38,26,22,12,21,40,26,32],[4,6,8],{6:STAT},58)
sh=grid(wb,"Requirements","194 inherited requirements — applicability and design allocation","BASELINE TEXT UNCHANGED • Fill actual applicability, owner, design and verification. Complete control selection is separate; source IDs resolve in the frozen reference.",
["Requirement ID","Exact inherited wording","Reference owner","Parent sections","Source IDs","Reference tests","Applicability","Actual owner","Design record","Verification assertions","Disposition / exception"],
[[x["requirementId"],x["text"],x["ownerRole"],x["parentSections"],x["sourceIds"],x["baselineTests"],"Unresolved","","","",""] for x in data["requirements"]],
[15,64,25,30,19,34,20,24,30,36,36],[7,8,9,10,11],{7:["Unresolved","Applicable","Not applicable","Inherited","Shared"]},78)
decrows=[[x["decisionId"],x["question"],x["requiredOwnerRoles"],"",x["requiredEvidence"],x["document"],"Not issued","",""] for x in data["site_decisions"]]
decrows += [[f"D14-{i:02d}",x["decision"],"Actual owner to assign","",x["record_to_complete"],"WD §14","Not issued","",x["blocking_point"]] for i,x in enumerate(data["open_v14_decisions"],1)]
grid(wb,"Decisions","Architecture and site decisions","12 inherited Dxx decisions plus six separately identified D14 records. D14 identifiers are kit indexes, not a silent renumbering of the source.",
["ID","Decision to resolve","Owner role","Actual selection","Required basis / evidence","Source home","Decision","Issuer / reference","Blocking gate / condition"],decrows,
[13,36,32,40,48,25,20,28,35],[4,7,8,9],{7:["Not issued","Proposed","Approved","Rejected","Conditional","Superseded"]},65)
grid(wb,"Views","Architecture view coverage","Each view must identify components, connections, authority/failure boundaries and assumptions; link to a controlled diagram or table.",
["ID","View","Question answered","Minimum contents","Baseline","Status","Actual artifact / revision","Reviewer"],
[[x['id'],x['view'],x['question'],x['required_content'],x['baseline'],"Not started","",""] for x in data["views"]],
[12,29,42,44,23,22,32,24],[6,7,8],{6:STAT},58)
risk_topics=[
("R-01","Native inter-domain routing bypass","Connected, distributed or more-specific routes can avoid the selected ZIP.","Network/security","RA §§8,16–18; WD §6"),
("R-02","Shared service becomes transit","Service forwarding, broad return routes or overbroad entitlement exposes other scopes.","Service/security","WD §§2,6–7"),
("R-03","Compromised privileged executor","One execution identity spans independent foundations and tenants.","Identity/automation","RA §§6,20,24"),
("R-04","Co-residency differs after restart","Scheduler, evacuation or recovery moves a workload outside approved eligibility.","Platform/security","RA §§7,11; WD §12"),
("R-05","Shared storage/controller compromise","Logical VM placement conceals controller, data, key or management sharing.","Storage/platform","RA §§11–13"),
("R-06","Recovery dependency cycle","Keys, catalogue, source or identity needed for recovery exist only on the failed platform.","Recovery/trust","RA §§13–14; SVC §6"),
("R-07","Unsupported native combination","Product features, gateway modes, versions or entitlements are assumed compatible.","Platform engineering","VND §7; KIT-TN-01"),
("R-08","Hidden family or MTU gap","IPv6, local protocols or surviving transport differs from the tested path.","Network engineering","NET §§3–4; WD §11"),
("R-09","Late task or competing writer","A timed-out native task later changes resources managed by a new executor.","Implementation","PROV §5; WD §10"),
("R-10","Evidence does not match scope","Stale results, dead endpoints or unsupported N/A disposition appear as conformance.","Assurance","QUAL §5; WD §13"),
("R-11","Capacity promise lacks survivor headroom","Compute can fit while inspected edge, storage rebuild or service dependencies cannot.","Capacity owner","QUAL §3; WD §11"),
("R-12","Retirement destroys required copy or key","Live workload deletion is confused with final data disposition.","Data/backup","RA §27; WD §12"),
("R-13","Supply or support access compromise","Update artifacts, vendor sessions or diagnostics leave the approved trust boundary.","Platform/security","RA §§13,25–26"),
("R-14","Operational readiness deferred","Production activates before accepted owners, restore proof or applicable authority.","Service owner","WD §9"),
]
grid(wb,"Risk_Workshop","Architecture risk workshop prompts","PROPOSED THREAT PROMPTS • Not findings against a deployed system. Determine applicability, controls, likelihood/impact and residual acceptance locally.",
["ID","Risk prompt","Credible scenario","Owner role","Baseline","Actual applicability","Selected controls","Residual risk / decision","Evidence / review"],
[[*r,"Unresolved","","",""] for r in risk_topics],
[12,32,48,26,30,20,40,38,32],[6,7,8,9],{6:["Unresolved","Applicable","Not applicable"]},64)
controlareas=["Network/zone boundary","Tenant/admin access","Privileged management","Compute/firmware","Storage/copy isolation","Cryptography/key custody","Backup/recovery","Logging/time","Vulnerability/change","Facility/personnel/support"]
grid(wb,"Control_Allocation","Selected-control and inheritance record","Do not treat control-family mapping as assessment. Enter the exact adopted catalogue edition, control/enhancement, parameters and accepted evidence.",
["Area","Catalogue / edition","Selected control / enhancement","Parameters","Provider / tenant / shared","Actual owner","Implementation home","Inherited scope / source","Evidence / assessor disposition"],
[[a,"","","","Unresolved","","","",""] for a in controlareas],
[26,30,30,34,26,24,32,38,40],[2,3,4,5,6,7,8,9],{5:["Unresolved","Provider","Tenant","Shared","Inherited","Not applicable"]},58)
grid(wb,"Sources","Primary mechanism context and baseline","External references support scoped mechanism checks, not installed qualification. Date checked: 16 September 2026. Frozen baseline references live in 05_Reference_v1_4.",
["ID","Title","URL","Review scope"],
[[x['id'],x['title'],x['url'],x.get('review','')] for x in data["sources"]],
[10,42,60,55],[],row_height=60)
print("Architecture sheets built")

def dashboard(wb, name, title, intro, metrics, guide_rows):
    sh=wb.worksheets.add(name)
    sh.get_range("A1:H1").merge();sh.get_range("A1").values=[[title]]
    sh.get_range("A1:H1").format={"fill":NAVY,"font":{"bold":True,"color":"#FFFFFF","size":18},"row_height":34}
    sh.get_range("A2:H3").merge();sh.get_range("A2").values=[[intro]]
    sh.get_range("A2:H3").format={"wrap_text":True,"font":{"size":11,"color":INK},"row_height":25,"vertical_alignment":"center"}
    for rr,(label,formula) in enumerate(metrics,5):
        sh.get_range(f"A{rr}:D{rr}").merge();sh.get_range(f"A{rr}").values=[[label]]
        sh.get_range(f"E{rr}:F{rr}").merge();sh.get_range(f"E{rr}").formulas=[[formula]]
        sh.get_range(f"A{rr}:F{rr}").format={"fill":PALE,"font":{"size":12,"color":INK},"row_height":28}
        sh.get_range(f"E{rr}:F{rr}").format.font.bold=True
    base=6+len(metrics)
    for rr,(where,action) in enumerate(guide_rows,base):
        sh.get_range(f"A{rr}:B{rr}").merge();sh.get_range(f"C{rr}:H{rr}").merge()
        sh.get_range(f"A{rr}").values=[[where]];sh.get_range(f"C{rr}").values=[[action]]
        sh.get_range(f"A{rr}:H{rr}").format={"wrap_text":True,"font":{"size":11,"color":INK},"row_height":46}
    sh.get_range("A1:H50").format.column_width=14
    sh.freeze_panes.freeze_rows(3)
    sheet_meta[id(wb),name]=(8,base+len(guide_rows))
    return sh
dashboard(workbooks["Architecture"],"Start","ARCHITECTURE KIT | WORKING REGISTERS",
"Create one controlled project copy. Teal cells accept project decisions; inherited text and examples are reference material. Dashboard counts never issue an approval.",
[("Architecture deliverables",'=COUNTA(Deliverables!A6:A13)'),
 ("Accepted records entered",'=COUNTIF(Deliverables!F6:F13,"Accepted")'),
 ("Unresolved requirement applicability",'=COUNTIF(Requirements!G6:G199,"Unresolved")'),
 ("Decisions not issued",'=COUNTIF(Decisions!G6:G23,"Not issued")')],
[("1 • Scope","Complete HLD_and_Architecture_Review_Template.docx and assign actual owners."),
 ("2 • Allocate","Resolve all applicable requirements, diagram homes, control responsibility and verification."),
 ("3 • Decide","Review sharing, routing, failure, recovery, location, native realization and exceptions."),
 ("4 • Handoff","Issue an attributable G0/engineering handoff. Accepted status requires a decision reference."),
 ("Sources","The frozen v1.4 library controls the inherited design. K references identify additional mechanism checks."),
 ("Record discipline","Excel, Word and CSV do not automatically synchronize. Nominate the authoritative project record for each field.")])
# Engineering register skeletons
wb=Workbook.create();workbooks["Engineering"]=wb
e_del=[x for x in data["deliverables"] if x["discipline"]=="Engineering"]
grid(wb,"Deliverables","Engineering delivery register","WORKING RECORD • Resolve actual support, values and execution ownership before an affected build.",
["ID","Deliverable","Owner role","Actual owner","Gate","Status","Acceptance evidence","Decision reference","Baseline"],
[[x['id'],x['title'],x['owner_role'],"",x['gate'],"Not started",x['acceptance'],"",x['baseline']] for x in e_del],
[12,38,26,22,12,21,40,26,32],[4,6,8],{6:STAT},58)
roles=[
("SITE","Site / facility boundary","Site authority"),("FABRIC","Leaf/spine or selected transport","Network owner"),("OOB","Independent recovery access","Management owner"),
("MGMT","Protected management capacity","Platform/identity"),("HOST-O","Eligible OZ pool","Platform owner"),("HOST-R","Eligible RZ pool","Platform owner"),
("STORAGE","Backend and controller boundary","Storage owner"),("EDGE","Tenant/domain enforcement","Security-edge owner"),("SERVICE-EDGE","Service handoff enforcement","Service security owner"),
("DNS-TIME","Approved resolver/time","Network services"),("TRUST","Identity/PKI/KMS","Trust custodians"),("PROTECTION","Backup/catalogue/repository","Backup owner")]
grid(wb,"Site_Components","Actual site and dependency inventory","ROLE SEEDS ONLY • No devices, host counts, locations, versions or failure independence have been selected.",
["Role ID","Infrastructure role","Owner role","Actual component ID","Site / rack / failure group","Product / version","Management path","Power / network / storage dependencies","Evidence / status"],
[[*r,"","","","","","Unresolved"] for r in roles],
[16,31,25,26,36,28,35,46,34],[4,5,6,7,8,9],row_height=54)
grid(wb,"Bill_of_Materials","Bill of materials and support acceptance","Enter actual supported items and quantities. No example model or cost is a procurement recommendation.",
["Line","Role / required outcome","Selected manufacturer / model","Quantity","Unit","Firmware / driver","Compatibility evidence","Support / entitlement expiry","Delivery / custody","Owner / approval"],
[[f"BOM-{i:02d}",r[1],"",None,"","","","","",""] for i,r in enumerate(roles,1)],
[13,34,34,12,12,26,42,32,30,30],[3,4,5,6,7,8,9,10],row_height=54)
grid(wb,"Ports_Cables","Physical port, optic and cable schedule","Qualified personnel perform physical work using approved facility/manufacturer procedures. Record actual endpoints and independent failure groups.",
["Link ID","A device / port","B device / port","Role / tenant scope","Media / optics / speed","MTU definition / value","Teaming / multihoming","Rack / power dependency","Installation receipt","Owner"],
[[f"LINK-{i:02d}","","","","","","","","",""] for i in range(1,13)],
[15,28,28,30,30,30,31,35,32,24],list(range(2,11)),row_height=48)
grid(wb,"Networks","Actual addressing and network ownership","Do not copy EX_ documentation ranges here. IPv4-only, IPv6-only and dual-stack need independently supported complete paths.",
["Network ID","Domain / tenant / zone","Site / platform","Address-family mode","Actual prefix / allocation","Gateway / owner","DHCP / RA / DNS","VLAN / VNI / RT authority","Handoff / ZIP","Decision / evidence"],
[[f"NET-{i:02d}","","","Unresolved","","","","","",""] for i in range(1,13)],
[15,29,27,20,38,33,34,38,25,35],list(range(2,11)),{4:["Unresolved","IPv4-only","IPv6-only","Dual-stack"]},55)
grid(wb,"Routes","Actual forwarding and return-route design","Routes do not grant application permission. Include connected/distributed/default paths, source validation and stateful return ownership.",
["Route ID","Routing owner / context","Family","Destination / allowed set","Next hop / interface","Next component","Source / import restrictions","Return route / owner","Enforcement / policy","Failure behaviour","Evidence"],
[[f"RTE-{i:02d}","","Unresolved","","","","","","","",""] for i in range(1,13)],
[15,32,16,37,33,27,38,37,33,38,32],list(range(2,12)),{3:["Unresolved","IPv4","IPv6"]},60)
grid(wb,"Flows","Actual flow and service permission schedule","Record connection initiation and reply semantics. DNS TCP/UDP and other compound services require all applicable flows. No default allow.",
["Flow ID","Source identity","Destination / service","Initiation / reply","Protocol / ports / type-code","Family","TLS / authentication","Enforcement point","Authority / expiry","Expected denial","Evidence"],
[[f"FLOW-{i:02d}","","","","","Unresolved","","","","",""] for i in range(1,13)],
[15,30,34,34,35,18,34,31,34,37,30],list(range(2,12)),{6:["Unresolved","IPv4","IPv6","Both"]},60)
grid(wb,"Compute_Storage","Compute, storage and copy placement","Specify actual native eligibility for create, restart, evacuation, migration and restore. Guest IP policy does not by itself govern virtual-disk attachment.",
["Resource ID","Role / WSD / domain","Native pool / placement","vCPU / memory requirement","Storage class / amount","Image / boot / device","Key client / custody","Copy / backup / retention","Failure / restart constraints","Owner / evidence"],
[[f"RES-{i:02d}","","","","","","","","",""] for i in range(1,11)],
[15,31,37,32,32,36,38,38,44,30],list(range(2,11)),row_height=58)
grid(wb,"Service_Interfaces","Shared service and management interfaces","Seeded services are obligations to design, not provisioned endpoints. Separate consuming clients from platform, service and key administrators.",
["Service","Consumer / actual client","Consumption endpoint / protocol","Entitlement / data scope","Separate management path","Reply / source policy","Bootstrap / recovery dependency","Owner / evidence"],
[[s,"","","","","","",""] for s in ["DNS","Time","Identity","PKI","KMS","Log ingestion","Monitoring","Images / update","Backup capture","Backup data","File / object data"]],
[24,34,41,38,42,38,44,32],list(range(2,9)),row_height=58)
grid(wb,"Privilege_Ownership","Resource writer, privilege and custody schedule","One authoritative tool/owner per native object and sensitive subresource. Store custody references, not secrets.",
["Scope","Native resources / operations","Authoritative tool","Actual role / owner","Credential custody reference","Allowed API / network targets","Review / revocation","Competing writer disposition"],
[[s,"","","","","","",""] for s in ["P0 bootstrap","P1 fabric / OOB","P2 platform install","P3 security edge","P3 names / trust","P3 protection","P4 networks / mandatory policy","P5 workload / disks","P6 restore / retirement"]],
[26,42,32,29,39,43,35,43],list(range(2,9)),row_height=56)
grid(wb,"Dependencies","Failure, bootstrap and recovery dependencies","For each failure, name what remains available and how the dependency is recovered. A different component label is not proof of independence.",
["Dependency ID","Consuming component","Required service","Data / admin / bootstrap","Failure / partition scenario","Expected surviving behaviour","Independent recovery path","Accepted owner / evidence"],
[[f"DEP-{i:02d}","","","Unresolved","","","",""] for i in range(1,13)],
[16,31,31,28,43,44,43,35],list(range(2,9)),{4:["Unresolved","Data","Administration","Bootstrap","Recovery","Multiple"]},60)
grid(wb,"Stack_Tuples","Exact platform and integration support record","No tuple is prequalified. Record feature-level compatibility, enabled entitlements, topology and actual support evidence; do not use a moving latest version as a qualification record.",
["Track","Product / release","API / backend","Provider / version","Installer / lifecycle","Hardware / firmware / driver","Features / entitlement","Gateway / HA / topology","Support reference / limitation","Qualification"],
[[s,"","","","","","","","","Unqualified"] for s in ["Nutanix","VMware vSphere","VMware NSX","OpenStack distribution","OpenStack networking","Fabric / OOB","Security edge","Storage / backup","Identity / PKI / KMS","IPAM / DNS / logging"]],
[23,30,30,33,34,42,38,38,48,20],list(range(2,11)),{10:["Unqualified","Candidate","Testing","Qualified","Restricted","Expired","Revoked"]},64)
ops=[
("Nutanix","VPC / external attachment / route","Platform/network"),("Nutanix","Security policy / categories","Platform/security"),("Nutanix","VM / disk / placement","Platform"),
("vSphere","VM / disk / placement","Platform"),("NSX","Segment / gateway / routing","Platform/network"),("NSX","Mandatory groups / policies","Platform/security"),
("OpenStack","Project / identity / quota","Cloud identity"),("OpenStack","Router / subnet / port","Cloud network"),("OpenStack","Mandatory security / port settings","Cloud security"),("OpenStack","Instance / volume / image","Cloud compute/data"),
("Shared","ZIP context / route / policy","Security edge"),("Shared","IPAM / DNS","Network services"),("Shared","Backup / retention / restore","Backup"),("Shared","Keys / certificates / identity","Trust"),("Fabric","Underlay / EVPN / attachment","Network")]
grid(wb,"Operation_Coverage","Operation-level tool coverage","Unknown is not supported. Record the supported alternative and ownership for every operation the selected provider cannot safely manage.",
["Track","Native resource scope","Owner role","Observe","Create","Update","Adopt / import","Replace","Delete","Unknown outcome recovery","Tool / tuple / source","Accepted alternative / limitation"],
[[*r]+["Unknown"]*7+["",""] for r in ops],
[20,36,25,17,17,17,20,18,17,30,42,48],[4,5,6,7,8,9,10,11,12],
{j:["Unknown","Supported - evidence linked","Native owner","Unsupported","Not applicable"] for j in range(4,11)},64)
print("Engineering schedules built")

# Capacity and MTU models: actual inputs blank; all derived outputs are formulas.
wb=workbooks["Engineering"]
units=[("Memory","GiB"),("Compute guarantee","vCPU-equivalent"),("Usable storage","GiB"),("Inspected throughput","Gbps"),("Concurrent sessions","sessions"),("Attachment capacity","slots")]
sh=grid(wb,"Capacity_Calc","Actual survivor-capacity admission calculation",
"ACTUAL INPUTS REQUIRED • Use the same measured failure scenario and units in every row. Existing commitment is not utilization plus reservation counted twice. Formula results are arithmetic only, not service authorization.",
["Resource dimension","Unit","Surviving qualified capacity","Operational reserve","Existing commitment","Proposed increment","Headroom after allocation","Arithmetic result","Failure scenario / evidence"],
[[a,u,None,None,None,None,None,None,""] for a,u in units],
[26,22,24,22,22,22,27,25,46],[3,4,5,6,9],row_height=58)
for r in range(6,12):
    sh.get_range(f"G{r}").formulas=[[f'=IF(COUNT(C{r}:F{r})<4,"INPUT REQUIRED",C{r}-D{r}-E{r}-F{r})']]
    sh.get_range(f"H{r}").formulas=[[f'=IF(COUNT(C{r}:F{r})<4,"INPUT REQUIRED",IF(MIN(C{r}:F{r})<0,"INVALID INPUT",IF(G{r}<0,"EXCEEDS CAPACITY","WITHIN MODEL")))']]
sh.get_range("C6:G11").set_number_format("#,##0.00")
sh.get_range("G6:G11").conditional_formats.add_cell_is({"operator":"lessThan","formula":0,"format":{"fill":"#FDE7D9","font":{"color":"#A03216"}}})
sh.get_range("A14:F14").merge();sh.get_range("A14").values=[["All-dimension arithmetic screen (not approval)"]]
sh.get_range("G14:I14").merge();sh.get_range("G14").formulas=[['=IF(COUNT(C6:F11)<24,"INPUT REQUIRED",IF(COUNTIF(H6:H11,"INVALID INPUT")>0,"INVALID INPUT",IF(COUNTIF(H6:H11,"EXCEEDS CAPACITY")>0,"LIMIT EXCEEDED","WITHIN ENTERED MODEL")))']]
sh.get_range("A14:I14").format={"fill":PALE,"font":{"bold":True,"color":INK},"row_height":28}
sh.get_range("A16:I17").merge();sh.get_range("A16").values=[["Input evidence must include measured workload/security features, node/rack/site loss, rebuild and maintenance load. This arithmetic does not model correlated failures, oversubscription safety, performance contention or physical product minima."]]
sh.get_range("A16:I17").format={"wrap_text":True,"row_height":25}
sh=grid(wb,"MTU_Calc","Actual path MTU budget",
"ACTUAL INPUTS REQUIRED • All dimensions are bytes of the outer IP packet, not link-frame MTU. Enter each actual encapsulation/header and the smallest active/surviving outer-IP path limit. Do not substitute a universal VXLAN figure for Geneve/IPsec.",
["Path ID","Workload IP bytes","Inner link header bytes","Tunnel header bytes","Transport header bytes","Outer IP header bytes","Extra tags / options bytes","Other encapsulation bytes","Outer IP total","Path outer-IP limit","Margin","Arithmetic result","Definition / evidence"],
[[f"MTU-{i:02d}"]+[None]*10+[None,""] for i in range(1,7)],
[15,22,23,22,25,24,26,26,21,23,18,25,43],[2,3,4,5,6,7,8,10,13],row_height=58)
for r in range(6,12):
    sh.get_range(f"I{r}").formulas=[[f'=IF(COUNT(B{r}:H{r})<7,"INPUT REQUIRED",SUM(B{r}:H{r}))']]
    sh.get_range(f"K{r}").formulas=[[f'=IF(OR(COUNT(B{r}:H{r})<7,COUNT(J{r})<1),"INPUT REQUIRED",J{r}-I{r})']]
    sh.get_range(f"L{r}").formulas=[[f'=IF(OR(COUNT(B{r}:H{r})<7,COUNT(J{r})<1),"INPUT REQUIRED",IF(OR(MIN(B{r}:H{r})<0,J{r}<=0,B{r}<=0),"INVALID INPUT",IF(K{r}<0,"EXCEEDS PATH","WITHIN MODEL")))']]
sh.get_range("B6:K11").set_number_format("#,##0")
sh.get_range("K6:K11").conditional_formats.add_cell_is({"operator":"lessThan","formula":0,"format":{"fill":"#FDE7D9"}})
sh=grid(wb,"EX_Fixture","EXAMPLE ONLY | fixture demand and independent probe plan",
"WD v1.4 §11 • These are requested guest resources, not actual site allocations, platform minima, raw storage, licensed capacity or total provider demand. Derived values are formulas.",
["Endpoint role","Count","vCPU each","Memory GiB each","Boot GiB each","Data GiB each","Total vCPU","Total memory GiB","Total virtual disk GiB"],
[["Processors",2,2,4,40,0,None,None,None],["Data endpoints",2,2,4,40,100,None,None,None],
 ["Sequential probes",1,2,4,40,0,None,None,None],["Alternative simultaneous probes",4,2,4,40,0,None,None,None]],
[31,12,15,21,19,19,18,23,28],[2,3,4,5,6],row_height=48)
for r in range(6,10):
    for c,f in [('G',f'=B{r}*C{r}'),('H',f'=B{r}*D{r}'),('I',f'=B{r}*(E{r}+F{r})')]:
        sh.get_range(f"{c}{r}").formulas=[[f]]
for r,title,sel in [(12,"Permanent fixture",(6,7)),(13,"Peak sequential test",(6,7,8)),(14,"Alternative simultaneous test",(6,7,9))]:
    sh.get_range(f"A{r}:F{r}").merge();sh.get_range(f"A{r}").values=[[title]]
    for c in "GHI":sh.get_range(f"{c}{r}").formulas=[['='+'+'.join(c+str(i) for i in sel)]]
sh.get_range("A12:I14").format={"fill":PALE,"font":{"bold":True,"color":INK},"row_height":28}
sh.get_range("A17:I18").merge();sh.get_range("A17").values=[["Exclude the alternative simultaneous-probe row from the sequential peak. Add actual controllers, service/security resources, replication, snapshots, backups, rebuild and maintenance reserve separately. Source: frozen WD §11; 07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx."]]
sh.get_range("A17:I18").format={"wrap_text":True,"row_height":27}
sh=grid(wb,"EX_MTU","EXAMPLE ONLY | packet-field arithmetic",
"Derived from WD §11: untagged inner Ethernet + basic VXLAN + UDP. Actual product definitions, Geneve options, IPsec and surviving paths need independent engineering. No operational setting is supplied.",
["Case","Workload IP","Inner Ethernet","VXLAN","UDP","Outer IP","Inner tag","Total outer IP","Outer-IP limit","Margin","Arithmetic result"],
[["IPv4 outer",1450,14,8,8,20,0,None,1500,None,None],
 ["IPv6 outer",1450,14,8,8,40,0,None,1500,None,None],
 ["IPv4 + inner tag",1450,14,8,8,20,4,None,1500,None,None]],
[29,20,21,16,14,18,18,24,23,18,25],[2,3,4,5,6,7,9],row_height=48)
for r in range(6,9):
    sh.get_range(f"H{r}").formulas=[[f'=SUM(B{r}:G{r})']]
    sh.get_range(f"J{r}").formulas=[[f'=I{r}-H{r}']]
    sh.get_range(f"K{r}").formulas=[[f'=IF(J{r}<0,"EXCEEDS PATH","WITHIN MODEL")']]
sh.get_range("J6:J8").conditional_formats.add_cell_is({"operator":"lessThan","formula":0,"format":{"fill":"#FDE7D9"}})
sh=grid(wb,"EX_Capacity","EXAMPLE ONLY | a bottleneck cannot be traded across dimensions",
"Proposed kit numbers, not WD measurements. The example has enough memory/storage but insufficient inspected throughput. Gbps does not substitute for sessions, routes, attachment slots or recovery capability.",
["Dimension","Unit","Surviving capacity","Reserve","Existing commitment","Increment","Remaining","Arithmetic result"],
[["Memory","GiB",128,16,60,20,None,None],["Usable storage","GiB",2000,300,800,400,None,None],["Inspected edge","Gbps",10,2,6,3,None,None]],
[28,18,24,20,24,21,22,25],[3,4,5,6],row_height=48)
for r in range(6,9):
    sh.get_range(f"G{r}").formulas=[[f'=C{r}-D{r}-E{r}-F{r}']]
    sh.get_range(f"H{r}").formulas=[[f'=IF(G{r}<0,"EXCEEDS CAPACITY","WITHIN MODEL")']]
sh.get_range("G6:G8").conditional_formats.add_cell_is({"operator":"lessThan","formula":0,"format":{"fill":"#FDE7D9"}})
for name,key,title in [("EX_Routes4","routes4","Illustrative IPv4 route schedule"),("EX_Routes6","routes6","Illustrative IPv6 route schedule"),("EX_Flows","flows","Illustrative service permissions"),("EX_Handoffs","handoffs","Illustrative handoff inventory")]:
    fields=list(data[key][0])
    rows=[[x.get(f,"") for f in fields] for x in data[key]]
    grid(wb,name,"EXAMPLE ONLY | "+title,"Frozen WD v1.4 companion schedule, unchanged. Addresses and next hops are documentation values, not site allocations or proof of native support.",
         [f.replace("_"," ").title() for f in fields],rows,[25 if len(fields)>3 else 35]+[38]*(len(fields)-1),[],row_height=58)
recovery_params=["Service measurement boundary","Uptime indicator/window/maintenance","Covered node/rack/site failure","RTO start/end scope","RPO consistency/data-loss interval","Initial required restore proof","Continuing recovery cadence","Evidence freshness after change","Copy retention / hold","Key lifetime / custody","Logging loss/buffering","Failback and writer control"]
grid(wb,"Service_Parameters","Actual service, recovery and evidence parameters","All actual values remain unresolved. Do not adopt historical numerical examples without owner approval and measured feasibility.",
["Parameter","Actual approved value / unit","Source / rationale","Measurement method","Owner / authority","Effective / review","Evidence"],
[[x,"","","","","",""] for x in recovery_params],
[34,36,40,43,32,27,38],[2,3,4,5,6,7],row_height=58)
dashboard(wb,"Start","ENGINEERING KIT | BUILD SCHEDULES",
"Keep actual site records separate from EX_ illustrative sheets. Teal cells are working inputs; calculations provide arithmetic screens only. Unknown support and empty inputs remain visible.",
[("Engineering deliverables",'=COUNTA(Deliverables!A6:A14)'),
 ("Accepted records entered",'=COUNTIF(Deliverables!F6:F14,"Accepted")'),
 ("Unqualified stack records",'=COUNTIF(Stack_Tuples!J6:J15,"Unqualified")'),
 ("Unknown operation dispositions",'=COUNTIF(Operation_Coverage!D6:J20,"Unknown")')],
[("1 • Actual design","Complete the LLD Word template with site, physical, routing, data, management and failure records."),
 ("2 • Supported tuple","Populate Stack_Tuples and Operation_Coverage, including native owners and unsupported operations."),
 ("3 • Capacity","Use Capacity_Calc and MTU_Calc with measured actual inputs. Empty fields deliberately do not produce a fit."),
 ("4 • Examples","EX_ sheets contain WD schedules and labelled new arithmetic examples. Never use them as operational allocations."),
 ("5 • Release","Link each build and verification procedure to approved artifacts, safe stops and evidence."),
 ("Sources","Baseline: 05_Reference_v1_4; new support check KIT-TN-01 and source K09 apply to the actual NSX tuple.")])
print("Engineering calculators and examples built")

wb=Workbook.create();workbooks["Implementation"]=wb
i_del=[x for x in data["deliverables"] if x["discipline"]=="Implementation"]
grid(wb,"Deliverables","Implementation delivery register","WORKING RECORD • Status records progress; actual evidence and authority must be linked separately.",
["ID","Deliverable","Owner role","Actual owner","Gate","Status","Completion criteria","Actual evidence","Decision reference"],
[[x["id"],x["title"],x["owner_role"],"",x["gate"],"Not started",x["acceptance"],"",""] for x in i_del],
[14,39,29,24,22,22,46,37,32],[4,6,8,9],{6:STAT},62)
packs=[
("P0","Bootstrap / trust","Bootstrap owner","G0 for affected scope","Restricted access, minimum trusted services and independent recovery."),
("P1","Physical foundation","Foundation owner","P0; accepted site design","OOB, fabric, physical routing/attachments, observed management and failure scope."),
("P2","Native platform","Selected platform owner","G1; approved bootstrap dependencies","Installed tuple, eligible pools, storage/overlay and actual native ownership."),
("P3","Security / common services","Service and edge owners","Accepted transport; coordinated P2 installation","Boundaries, named services, identity/keys/logging/protection; joint P2/P3 G2 acceptance."),
("P4","Tenant / domain","Platform and security owners","G2 for ordinary production; separate restricted-fixture path","Owned scope, addresses, networks, routes and mandatory policy under deny."),
("P5","Workload / activation","Service acceptance owner","P4; current tests; initial G4 and operating authority before production G3","Owned VMs/disks/services, verified boundaries and controlled activation."),
("P6","Change / retirement","Lifecycle and data owners","Accepted current scope and authorized change","Safe maintenance/recovery/migration/retirement with retained obligations.")]
grid(wb,"Work_Packages","P0–P6 execution and accepted handoffs","Installation dependencies are not permission to offer production. Keep separate owners, actual artifacts and handoffs.",
["ID","Work package","Owner role","Prerequisites","Required handoff","Actual owner","Status","Receipt / limitations"],
[[*r,"","Not started",""] for r in packs],
[12,26,30,50,54,26,22,42],[6,7,8],{7:STAT},64)
steps=json.loads((root/"source/runbook_catalogue.json").read_text())
grid(wb,"Build_Steps","Reference methods — actual execution record","61 site-parameterized steps from 10 runbooks. Fill actual target, approved artifact, operator and evidence. There are no executable vendor commands or supplied permissions.",
["Step ID","Runbook","Reference step","Owner role","Action / expected observation","Stop / preserve","Actual target / artifact","Actual operator","Status","Native task / UTC","Evidence / disposition"],
[[x["step_id"],x["runbook"],x["title"],x["owner_role"],x["action"]+" Expected: "+x["expected"],x["stop"],"","","Not run","",""] for x in steps],
[15,13,35,32,60,49,42,25,21,36,41],[7,8,9,10,11],{9:["Not run","Running","Completed","Failed","Blocked","Unknown outcome","Not applicable"]},92)
obs=[]
for x in data["tests"]:
    obs.append((x["id"],"CT procedure",x["title"],x["expected"],"; ".join(x["requirements"]),"Historical CT catalogue; actual applicability required"))
for x in data["addenda"]:
    obs.append((x["id"],"Realization addendum",x["title"],x["expected"],"; ".join(x["baseTests"]),"Historical realization addenda; actual applicability required"))
for x in data["assertions"]:
    ident=x["assertion"].split(" / ")[0]
    obs.append((ident,"Worked-design assertion",x["assertion"],x["observation"],x["mapped_procedures_and_status"],"WD v1.4 §13"))
grid(wb,"Test_Applicability","Reference procedures and assertions — applicability","80 CT procedures + 12 realization addenda + 12 W14 assertions. These 104 rows are not 104 executed tests; a compound assertion can need multiple observations.",
["Reference ID","Record type","Title / assertion","Expected outcome","Inherited mappings","Source","Applicability","Actual service / tuple / family","Campaign stage","Rationale / approving authority"],
[[*r,"Unresolved","","",""] for r in obs],
[16,29,41,64,42,43,23,44,30,47],[7,8,9,10],{7:["Unresolved","Applicable","Not applicable","Partially applicable"]},88)
grid(wb,"Test_Results","Actual test execution and evidence","One starter row per reference. Duplicate a row with a new execution ID for another family, topology or assertion. Expected outcomes remain in Test_Applicability; never copy them into observations as a pass.",
["Execution ID","Reference ID","Result","Actual tuple / topology","Preconditions / healthy control","Observed result / UTC","Evidence reference / digest","Reviewer / authority","N/A rationale / defect"],
[[f"EXEC-{i:03d}",r[0],"Not run","","","","","",""] for i,r in enumerate(obs,1)],
[17,18,20,43,48,56,45,37,47],[3,4,5,6,7,8,9],{3:["Not run","Passed","Failed","Blocked","Not applicable"]},64)
sh=grid(wb,"Evidence_Index","Actual evidence inventory and protection","Blank template rows contain no supplied evidence or fake digest. Store protected artifacts outside this workbook and record authoritative references.",
["Evidence ID","Execution / change / requirement","Actual artifact reference","Digest / integrity method","Target / scope / revision","Observed UTC / collector","Classification / access / retention","Reviewer / freshness disposition"],
[[f"EVD-{i:03d}","","","","","","",""] for i in range(1,21)],
[17,39,49,45,42,38,49,44],list(range(2,9)),row_height=60)
grid(wb,"Defects","Observed defects and deviations","Unpopulated actual finding register. Reference threat prompts in the architecture kit are not live vulnerabilities.",
["Defect ID","Observed fact / scope","Expected design / requirement","Impact / priority rationale","Actual owner","Status","Recovery / correction","Retest evidence","Disposition authority / deadline"],
[[f"DEF-{i:03d}","","","","","Not raised","","",""] for i in range(1,13)],
[16,51,44,43,26,22,43,36,43],[2,3,4,5,6,7,8,9],{6:["Not raised","Open","In remediation","Ready for retest","Resolved","Risk accepted","Closed"]},62)
grid(wb,"Gate_Decisions","Gate and operating authority decisions","NO AUTOMATIC APPROVAL • G4 initial readiness is a production G3 prerequisite; continuing G4 afterwards is not a substitute. Restricted fixture permission is separate.",
["Gate ID","Purpose","Owner role","Required prior scope","Evidence / required records","Actual decision","Issuer / record","Validity / conditions","Actual evidence"],
[[x["id"],x["purpose"],x["decision_owner"],x["prerequisites"],x["required_records"],"Not issued","","",""] for x in data["gates"]],
[19,32,39,53,58,23,39,47,44],[6,7,8,9],{6:["Not issued","Approved","Rejected","Conditional","Suspended","Superseded"]},82)
handover_items=[
("H01","Named service/operations/data/security owners","Actual contacts, escalation and on-call coverage"),
("H02","Accepted as-built and native ownership","Topology, versions, resource identities and tool/writer responsibilities"),
("H03","Accepted service and failure envelope","Actual limits, SLO, RTO/RPO, maintenance and capacity basis"),
("H04","Monitoring and evidence protection","Event/health coverage, loss behaviour, access and retention"),
("H05","Incident and containment authority","Scoped response, emergency paths and explicit release"),
("H06","Credential, certificate and key custody","Protected references, role separation, revocation and tested recovery"),
("H07","Backup/catalogue and initial restore proof","Accepted consistency, retained copies, key access and measured recovery"),
("H08","Support and lifecycle readiness","Compatible patch/change method, support expiry and supplier access"),
("H09","Retained data and disposal responsibilities","Holds, copy lineage, owners, key lifetime and sanitization"),
("H10","Actual initial G4 decision","Scope-specific reviewed evidence and attributable authority before G3")]
grid(wb,"Handover","Operational handover and initial readiness","Complete applicable initial readiness before production; post-activation handover confirms an already accepted scope.",
["ID","Readiness area","Required record","Actual owner","Status","Evidence","Decision / condition"],
[[*r,"","Not started","",""] for r in handover_items],
[12,40,52,26,22,45,44],[4,5,6,7],{5:STAT},58)
grid(wb,"Recovery_Record","Actual recovery, migration and failback results","Service scope and consistency matter. All initial result fields remain Not run; no RTO/RPO or product support is pre-certified.",
["Exercise ID","Failure / source / target","Scope / RTO / RPO definition","Writer / fencing evidence","Keys / catalogue / dependencies","Actual recovered point / time","Data / security acceptance","Result","Authority / evidence"],
[[f"REC-{i:02d}","","","","","","","Not run",""] for i in range(1,9)],
[17,44,46,45,46,43,43,22,43],[2,3,4,5,6,7,8,9],{8:["Not run","Passed","Failed","Blocked","Not applicable"]},64)
grid(wb,"Retained_Copies","Retained copies, holds, keys and disposition","Live-service retirement is separate from disposal of all data. Populate actual copies and obligations; identifiers below are empty record slots.",
["Record ID","Former WSD / copy identity","Location / access scope","Retention / hold / owner","Required key / catalogue","Approved live cleanup","Sanitization method / evidence","Remaining obligation / next review"],
[[f"COPY-{i:02d}","","","","","","",""] for i in range(1,11)],
[16,39,43,46,43,41,47,51],list(range(2,9)),row_height=62)
grid(wb,"Change_Log","Controlled change and approval-impact register","A material change can invalidate previous qualification or evidence. Record the affected scope and actual authority rather than rewriting history.",
["Change ID","Date / owner","Scope / baseline revision","Affected architecture / interfaces","Build / rollback / safe stop","Required re-verification","Approval / execution evidence","Status"],
[[f"CHG-{i:02d}","","","","","","","Not started"] for i in range(1,11)],
[17,30,43,47,52,47,46,22],list(range(2,9)),{8:STAT},60)
dashboard(wb,"Start","IMPLEMENTATION KIT | EXECUTION AND ACCEPTANCE",
"Assign actual scope, owners and evidence before execution. All reference procedures start not run; no gate decision is supplied. Counts are record-quality indicators, never authorization.",
[("Implementation deliverables",'=COUNTA(Deliverables!A6:A15)'),
 ("Reference steps not run",'=COUNTIF(Build_Steps!I6:I66,"Not run")'),
 ("Unresolved applicability",'=COUNTIF(Test_Applicability!G6:G109,"Unresolved")'),
 ("Test result rows not run",'=COUNTIF(Test_Results!C6:C109,"Not run")'),
 ("Gate decisions not issued",'=COUNTIF(Gate_Decisions!F6:F12,"Not issued")')],
[("1 • Preflight","Use RB-00 and IT §1. Identify the authorized target and controlled engineering release."),
 ("2 • Commission","Select P0–P6 work and one vendor track; preserve native ownership and dependency handoffs."),
 ("3 • Qualify","Restricted disposable fixtures generate observations; they cannot authorize production."),
 ("4 • Ready / activate","G0/G1/G2 and applicable initial G4 plus current tests and valid operating authority precede production G3."),
 ("5 • Evidence","Use distinct execution IDs for each actual run and record actual scope, result, reviewer and protected artifact."),
 ("6 • Operate","Handover current as-built, recovery, support, incidents, capacity and retained obligations; re-evaluate material changes.")])
print("Implementation tracker built:",len(obs),"reference records")

# Final polish and compact verification; this is the same in-memory workbook state.
for name,wb in workbooks.items():
    sh=wb.worksheets.get_item("Start")
    sh.get_range("A5:H20").format.vertical_alignment="center"
reports={}
for name,wb in workbooks.items():
    errors=wb.inspect({"kind":"match","search_term":"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!","options":{"use_regex":True,"max_results":50},"summary":"Formula error scan"})
    reports[name]={"formula_error_scan":errors.ndjson,"sheets":wb.inspect({"kind":"sheet","include":"id,name"}).ndjson}
    print(name,errors.ndjson[:500])
print(workbooks["Engineering"].inspect({"kind":"table","range":"EX_Capacity!G6:H8","include":"values,formulas","table_max_rows":3,"table_max_cols":2}).ndjson)
print(workbooks["Engineering"].inspect({"kind":"table","range":"EX_MTU!H6:K8","include":"values,formulas","table_max_rows":3,"table_max_cols":4}).ndjson)
print(workbooks["Engineering"].inspect({"kind":"table","range":"MTU_Calc!I6:L7","include":"values,formulas","table_max_rows":2,"table_max_cols":4}).ndjson)
# Record the local formula inspection before exporting the final workbooks.
(root/"07_Quality/workbook_checks.json").write_text(json.dumps(reports,indent=2))
print("Verification recorded")
# Final formatting and source-scope correction.
workbooks["Architecture"].worksheets.get_item("Sources").get_range("D6:D16").values = [[x["review_scope"]+" Reviewed "+x["reviewed"]+"." ] for x in data["sources"]]
for label,wb in workbooks.items():
    for (wid,name),(nc,nr) in list(sheet_meta.items()):
        if wid != id(wb) or name == "Start":
            continue
        sh=wb.worksheets.get_item(name)
        vals=sh.get_range(f"A6:{col(nc)}{nr}").values
        widths=[sh.get_range(f"{col(j)}1").format.column_width for j in range(1,nc+1)]
        for i,row in enumerate(vals,6):
            lines=max([1]+[sum(max(1,math.ceil(len(part)/max(8,float(widths[j])*0.9))) for part in str(v).split("\n")) for j,v in enumerate(row) if v is not None])
            sh.get_range(f"A{i}:{col(nc)}{i}").format.row_height=min(180,max(38,lines*13+9))
    wb.worksheets.get_item("Start").get_range("A5:H20").format.vertical_alignment="center"

for label,wb in workbooks.items():
    target={"Architecture":"01_Architecture/Architecture_Registers.xlsx","Engineering":"02_Engineering/Engineering_Schedules.xlsx","Implementation":"03_Implementation/Implementation_Tracker.xlsx"}[label]
    SpreadsheetFile.export_xlsx(wb).save(str(root/target))
