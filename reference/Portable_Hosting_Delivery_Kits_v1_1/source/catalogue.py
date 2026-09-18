from pathlib import Path
import csv,json,re
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'05_Reference_v1_4'
def csvread(p):
    with open(p,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def csvwrite(p,fields,rows):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
DOCS={
'DEL':('00_Delivery_Map.docx','Delivery Map and Acceptance Gates'),
'AK':('01_Architecture/Architecture_Kit.docx','Architecture Kit — Design, Decisions and Approval'),
'AT':('01_Architecture/HLD_and_Architecture_Review_Template.docx','High-Level Design and Architecture Review Template'),
'EK':('02_Engineering/Engineering_Kit.docx','Engineering Kit — Buildable Design and Verification'),
'ET':('02_Engineering/LLD_and_Engineering_Review_Template.docx','Low-Level Design and Engineering Review Template'),
'VC':('02_Engineering/Vendor_Realization_Cards.docx','Vendor Realization and Shared-Infrastructure Cards'),
'IK':('03_Implementation/Implementation_Kit.docx','Implementation Kit — Commission, Qualify and Operate'),
'IT':('03_Implementation/MOP_Test_and_Handover_Template.docx','Method of Procedure, Test and Handover Templates'),
'EX':('04_Shared/Worked_Delivery_Example.docx','Worked Delivery Example — From Decision to Evidence')}
BFILES={p.name.split('_',1)[0]:p.name for p in BASE.glob('*.docx')}
BASEMAP={
'RA':('00_Reference_Architecture_v1_4.docx','RA_s_{:03d}'),
'GM':('01_Gap_Map_and_Decision_Register_v1_4.docx','GM_s_{:03d}'),
'NET':('02_Fabric_Security_and_Interfaces_v1_4.docx','NET_s_{:03d}'),
'VND':('03_Vendor_Stack_Realizations_v1_4.docx','VND_s_{:03d}'),
'PROV':('04_Provisioning_and_Commissioning_v1_4.docx','PROV_s_{:03d}'),
'SVC':('05_Shared_Services_Data_and_Recovery_v1_4.docx','SVC_s_{:03d}'),
'QUAL':('06_Site_Design_Qualification_and_Operations_v1_4.docx','QUAL_s_{:03d}'),
'WD':('07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx','WD14_S{:02d}')}
# Kit deliverables are proposed working records, not new government requirements.
DELIVERABLES=[
('AK-01','Architecture','Mandate, stakeholders and service envelope','Architecture lead','G0','RA §§1–4','AT §1','Named scope, beneficiaries, exclusions, demand and accountable service owner.'),
('AK-02','Architecture','Requirement applicability and acceptance allocation','Architecture + security','G0','RA §§1–2, 28','AT §2','Every selected baseline requirement has applicability, owner, design home and verification method.'),
('AK-03','Architecture','High-level physical, logical and security views','Infrastructure architect','G0','RA §§3–14','AT §§3–5','Components, connections, trust/authority/failure boundaries, data paths and assumptions are coherent.'),
('AK-04','Architecture','Architecture decisions and allowed variations','Architecture authority','G0','RA §29; GM §4','AT §6','Alternatives, rationale, consequences, affected requirements and actual decision authority recorded.'),
('AK-05','Architecture','Threat, co-residency and control responsibility','Security architect','G0','RA §§6–8, 11–13','AT §7','Sharing at each layer, credible failures/compromises, residual risks and inherited controls are assigned.'),
('AK-06','Architecture','Availability, recovery, capacity and location strategy','Service + data owners','G0','RA §§12–14, 26–27','AT §8','Offered service boundaries and objectives are separated from categorization; exit and recovery constraints explicit.'),
('AK-07','Architecture','Vendor realization and provisioning strategy','Platform architect','G0','RA §§15–24','AT §9','Native realization choices and P0–P6 responsibilities are linked without assuming one universal provider.'),
('AK-08','Architecture','Architecture review and engineering handoff','Architecture authority','G0','RA §§28–30','AT §10','Critical design decisions resolved or blocked by scope; signed disposition and engineering inputs available.'),
('EK-01','Engineering','Site LLD and controlled design release','Engineering lead','G1','RA §30; QUAL §2','ET §1','Actual values and source references replace examples; reviewed topology and controlled revision identified.'),
('EK-02','Engineering','Physical inventory, bill of materials and port/cable schedule','Site + network engineers','G1','RA §§3–6','ET §2','Hardware/optic/firmware/power dependencies, rack and link endpoints, support and staging accepted.'),
('EK-03','Engineering','Network, addressing, routes and ZIP paths','Network + security engineers','G2','RA §§5, 8–10; WD §§4–7','ET §§3–4','Forward/reply routes, service endpoints, enforcement, MTU and alternate paths recorded per family.'),
('EK-04','Engineering','Compute, storage and placement schedules','Platform + storage engineers','G2','RA §§7, 11–12','ET §5','Eligible hosts, native placement, virtual disk/data paths, copies and recovery membership are explicit.'),
('EK-05','Engineering','Management, shared-service and trust interfaces','Service + identity engineers','G2','RA §§6, 9, 13; SVC §§1–5','ET §6','Consumption/admin separation, initiating clients, role/key scope and bootstrap/recovery dependencies mapped.'),
('EK-06','Engineering','Capacity, performance, MTU and failure calculations','Capacity engineer','G2','QUAL §§3–4; WD §11','ET §7','Assumptions and measured survivor capacity share units and failure basis; all bottlenecks evaluated.'),
('EK-07','Engineering','Exact stack and operation-level automation coverage','Platform + automation engineers','G2','RA §§15–24; VND §7','ET §8','Products, APIs, providers, installers, hardware, entitlements and all lifecycle operations have a support disposition.'),
('EK-08','Engineering','Build, rollback and qualification design','Engineering + assurance leads','G2','PROV §§1–6; QUAL §5','ET §9','Site-specific MOP, rollback/forward repair, test resources and assertion coverage reviewed before execution.'),
('EK-09','Engineering','Engineering release and implementation handoff','Engineering release owner','G1/G2','RA §§25, 30','ET §10','Versioned design, artifacts, credentials references, evidence plan and unresolved blockers handed over explicitly.'),
('IK-01','Implementation','Change scope, release freeze and execution authority','Change owner','Before execution','PROV §§1, 5; WD §§9–10','IT §1','Actual change reference, immutable artifacts, scope, participants and stop authority recorded.'),
('IK-02','Implementation','Staging and installation readiness','Deployment lead','G1','RA §21','IK §3','Supplier/asset checks, approved installation method, facility work, recovery access and staging results accepted.'),
('IK-03','Implementation','P0–P1 bootstrap and foundation receipts','Foundation owner','G1','RA §21; PROV §2','IK §3','Trusted independent access, minimum services and verified physical/network transport precede platform consumption.'),
('IK-04','Implementation','P2 native platform build receipts','Selected platform owner','G2','RA §§16–18, 22','IK §4; VC §§2–4','Installer and native resource changes match approved tuple; APIs, baseline and supported recovery observed.'),
('IK-05','Implementation','P3 shared-service and boundary receipts','Service + edge owners','G2','RA §§9, 12–13, 22','IK §5','Denied boundary paths, service clients, return routing, names/trust/backup and management separation observed.'),
('IK-06','Implementation','Restricted qualification fixture and test campaign','Assurance lead','G2','WD §§9, 11, 13','IK §6; IT §4','Authorized disposable scope, actual observations and supporting control paths; no production qualification assumed.'),
('IK-07','Implementation','G4 initial operational and recovery readiness','Service operations owner','Before G3','WD §9; QUAL §§5, 7','IT §§5–6','Owners, support, monitoring, incident paths and required restore/recovery evidence accepted before activation.'),
('IK-08','Implementation','P4–P5 tenant build and production activation','Service acceptance owner','G3','RA §23; WD §9','IK §7; IT §7','G0/G1/G2, applicable initial G4, current tests and valid authority precede reversible activation.'),
('IK-09','Implementation','As-built, defect and evidence records','Implementation + operations','G3/G4','RA §§26, 28, 30','IT §§3–6','Actual identities, configurations, departures, tests, evidence and owner acceptance are attributable.'),
('IK-10','Implementation','P6 maintenance, migration and retirement','Lifecycle/data owners','G4 continuing','RA §§25–27','IK §§8–9; IT §8','Change requalification, fencing, retained-copy/key obligations, access withdrawal and safe disposal tracked.')]
GATES=[
('G0','Design adoption','Architecture authority','None','AK-01–AK-08; adopted controls and variation decisions','Proposed','No build authorization is implied by document acceptance.'),
('G1','Foundation acceptance','Foundation/service owner','G0 for affected scope','EK-01/02; IK-02/03; trusted access and transport evidence','Not evaluated','A reachable API is not a commissioned platform.'),
('Restricted fixture','Non-production test permission','Test/change authority','G1; installed safeguarded candidate resources','Test scope, disposable data, restoration plan, exact target and expiry','Not issued','May generate qualification evidence; cannot authorize production use.'),
('G2','Platform and shared-service qualification','Platform/service qualification authority','G0/G1; authorized fixture; applicable observed tests','EK-03–EK-09; IK-04–IK-06; actual supported tuple and measured envelope','Not evaluated','Installed resources and provider availability are not qualification.'),
('G4 initial','Operational/recovery readiness','Operations + data/service acceptance','Relevant qualified platform/service','IK-07; current owners, incident path, monitoring, keys/catalogue and required restore proof','Not evaluated','Must precede the production service promise; not deferred until after G3.'),
('G3','Production activation','Authorized service acceptance owner','G0, G1, G2, applicable G4 initial; valid authority','Current tenant build evidence, exposure scope, rollback/containment and acceptance','Not issued','Neither a workbook nor a Terraform exit code grants authority.'),
('G4 continuing','Continuing operations and reacceptance','Operations/service owner','Activated service; approved cadence and change triggers','Maintenance, drift, recovery exercises, incidents, support and retirement records','Not evaluated','Historical approval is not evidence for changed topology.')]
VIEWS=[
('V01','Context and service boundary','What service is offered and who owns each external dependency?','Sites, tenants, provider services, consumers, external authorities.','RA §§1–4'),
('V02','Physical deployment','Where are the equipment, links, power and shared failure dependencies?','Sites/racks, cells, OOB, host pools, storage, edges, control components.','RA §§3–6'),
('V03','Logical tenancy and security','Which independent authorities and zones exist?','Tenant/WSD/domain/instance/network, owner, sharing and trust transitions.','RA §§7–8'),
('V04','End-to-end forwarding and enforcement','Where do request and reply travel and where are they enforced?','Gateways, ZIPs, allowed prefixes, routes, NAT, policy and native bypass candidates.','RA §§8–10; WD §§4–7'),
('V05','Management and administrative authority','Who can change each component and by which protected path?','Privileged endpoint, management domain, roles, API/BMC, break-glass and logging.','RA §6'),
('V06','Compute and storage','Which resources and copies share hardware/control and how is placement enforced?','Pools, schedulers, virtual disks, file/object clients, copies, keys and protection.','RA §§11–13'),
('V07','Shared-service consumption','What is the consumer allowed to do and how does the service reply?','Service endpoint, client identity, return routes, backend authorization and admin plane.','RA §9; SVC §§1–5'),
('V08','Failure and recovery','Which failures are covered and which dependencies must survive?','Failure sets, quorum/fencing, independent trust, restored service scope and failback.','RA §14; SVC §6'),
('V09','Vendor realization','Which native components realize the same requirements on each selected stack?','Actual tuple, mechanisms, enforcement locations, support limits and alternatives.','RA §§15–19'),
('V10','Provisioning and lifecycle','What is installed, allocated, changed and retired by each owner?','P0–P6 resources, prerequisites, single-writer ownership, handoffs and safe stops.','RA §§20–25'),
('V11','Transition and operational model','How does the current environment become and remain the target?','Adoption waves, dependencies, capacity, operating responsibilities, exit and disposal.','RA §§25–30')]
SOURCES=[
('K01','Cloud network security zones (ITSP.80.023)','https://www.cyber.gc.ca/en/guidance/cloud-network-security-zones-itsp80023','Reviewed sections 1–4; supports scoped cloud-zoning and management considerations, not authorization.'),
('K02','ITSP.10.033 foreword, overview and introduction','https://www.cyber.gc.ca/en/guidance/cyber-security-privacy-risk-management/itsp10033/foreword-overview-introduction','Reviewed supersession statement; preserve exact control edition rather than silently joining legacy IDs.'),
('K03','Terraform providers within modules','https://developer.hashicorp.com/terraform/language/modules/develop/providers','Reviewed provider configuration and module boundaries; actual provider support remains environment-specific.'),
('K04','Terraform dependency lock file','https://developer.hashicorp.com/terraform/language/files/dependency-lock','Reviewed distinction between provider dependency locks and remote module selections.'),
('K05','Official Nutanix Terraform provider repository','https://github.com/nutanix/terraform-provider-nutanix','Reviewed README compatibility, feature and lifecycle notes; no provider version selected for a site.'),
('K06','OpenStack Neutron networking concepts','https://docs.openstack.org/neutron/latest/admin/intro-os-networking.html','Reviewed security-group/port concepts; latest documentation is a development branch, not a production pin.'),
('K07','OpenStack OVN reference architecture','https://docs.openstack.org/neutron/latest/admin/ovn/refarch/refarch.html','Reviewed role and routing model; selected distribution/backend must be independently qualified.'),
('K08','OpenStack Nova host aggregates','https://docs.openstack.org/nova/latest/admin/aggregates.html','Reviewed scheduling/aggregate controls; labels alone do not establish placement enforcement.'),
('K09','Broadcom KB 442835 — Tier-0 VRF and active-active stateful HA','https://knowledge.broadcom.com/external/article/442835/cannot-add-tier0-vrf-gateway-to-a-tier0.html','Official KB reviewed; explicit design limitation warrants a tuple-specific engineering check, not a production reconfiguration instruction.'),
('K10','Guidance on securely configuring network protocols (ITSP.40.062)','https://www.cyber.gc.ca/en/guidance/guidance-securely-configuring-network-protocols-itsp40062','Reviewed protocol-configuration scope; approved site configurations remain required.'),
('K11','Terraform plan command reference','https://developer.hashicorp.com/terraform/cli/commands/plan','Reviewed saved-plan handling; plan outputs can contain sensitive infrastructure values.')]
# Operational source facts are cited in documents; all kit process additions are local proposals.
DATA={
'deliverables':[dict(zip(['id','discipline','title','owner_role','gate','baseline','template','acceptance'],r),status='Not started',actual_owner='',evidence='') for r in DELIVERABLES],
'gates':[dict(zip(['id','purpose','decision_owner','prerequisites','required_records','status','limit'],r)) for r in GATES],
'views':[dict(zip(['id','view','question','required_content','baseline'],r),status='Not started',artifact='') for r in VIEWS],
'sources':[dict(zip(['id','title','url','review_scope'],r),reviewed='2026-09-16') for r in SOURCES],
'requirements':csvread(BASE/'registers/requirement_document_crosswalk.csv'),
'site_decisions':csvread(BASE/'registers/site_decisions.csv'),
'open_v14_decisions':csvread(BASE/'registers/v1_4_open_decisions.csv'),
'routes4':csvread(BASE/'registers/v1_4_ipv4_route_model.csv'),
'routes6':csvread(BASE/'registers/v1_4_ipv6_route_model.csv'),
'flows':csvread(BASE/'registers/v1_4_reference_flows.csv'),
'handoffs':csvread(BASE/'registers/v1_4_reference_handoffs.csv'),
'tests':json.loads((BASE/'registers/conformance_tests_reference.json').read_text()),
'addenda':json.loads((BASE/'registers/realization_verification_addenda.json').read_text()),
'assertions':csvread(BASE/'registers/v1_4_verification_assertions.csv')}
assert len(DATA['requirements'])==194
for k,v in DATA.items():
 if isinstance(v,list) and v and isinstance(v[0],dict):
  csvwrite(ROOT/'04_Shared'/f'{k}.csv',list(v[0]),[{kk:('; '.join(map(str,vv)) if isinstance(vv,list) else vv) for kk,vv in row.items()} for row in v])
(ROOT/'source/kit_catalogue.json').write_text(json.dumps(DATA,indent=2,ensure_ascii=False))
