#!/usr/bin/env python3
"""One-time seed of proposed audit allocations from the exact imported references.

Not a CI regeneration job. After seeding, edit the canonical records through review;
this migration refuses to overwrite them. No actual enforcement/approval is supplied.
"""
from pathlib import Path
import json,csv,re,copy
R=Path(__file__).resolve().parents[2];S=R/'sources/assurance';S.mkdir(parents=True,exist_ok=True)
if (S/'implementation_allocation.json').exists():raise SystemExit('Refusing to overwrite maintained allocation records')
shared=R/'reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared'
read=lambda p:list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
reqs=read(shared/'requirements.csv')
# These are proposed engineering allocations. Every assertion keeps its complete
# original requirement and an exact quoted focus; nothing is marked implemented.
# tuple: enforcement locus, delivery disposition, concrete candidate artifact(s), actual gap
profiles={}
def group(names,locus,disposition,artifacts,gap):
 for name in names.split():profiles[name]=(locus,disposition,artifacts,gap)
group('ARCH INV REF SCOPE CAT THR MODEL TEN WSD SDI ZONE ASSUR RESP','Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints','PARTIAL_DESIGN_AND_CANDIDATE', ['docs/architecture/RAD.md','docs/engineering/TAD.md','tools/input_review.py'], 'No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.')
group('DOC STD AUTH EXC OPS ONB ACPT','Architecture/security/service-owner review and controlled evidence/exception record systems','EXTERNAL_GOVERNANCE_OR_MANUAL_CONTROL',['docs/DOCUMENTATION_MIGRATION.md','docs/assurance/requirements.md'], 'Actual deciding authority, jurisdiction, applicability, issued approval, operating evidence and exception expiry handling must be supplied by the service owner; Git labels and test passes cannot issue them.')
group('ZIP EDGE','Actual two-sided boundary forwarding, stateful policy, inspection and management plane at EC/SE contexts','PARTIAL_CANDIDATE_NATIVE_SOURCE',['terraform/modules/nsx-gateway-quarantine/main.tf.json','tools/route_record_review.py'], 'Only candidate scoped NSX gateway DROP and route checks exist. A selected firewall/ZIP, required inspection, isolated native attachments, tenant administration and HA capacity remain unimplemented or unqualified.')
group('MGT','Physical/OOB interfaces, management routes, remote-access boundary and privileged identity service','EXTERNAL_NATIVE_FOUNDATION_REQUIRED',['docs/engineering/TAD.md','tools/nsx_observe.py','tools/nutanix_observe.py'], 'Readback tools do not construct management separation, hardened admin paths, supplier access, hardware OOB or independently recoverable identity. Native foundation implementation and path/role tests are absent.')
group('OVL MICRO','Native guest NIC/port policy, provider-owned selectors and domain routing, including same-host paths','PARTIAL_CANDIDATE_NATIVE_SOURCE',['terraform/modules/nutanix-domain/main.tf.json','terraform/modules/nsx-domain/main.tf.json','terraform/modules/openstack-domain/main.tf.json'], 'Selected denied-domain source is present. Actual native policy precedence, delegated mutation role, arbitrary NIC/selector bypass and effective same-host/cross-host enforcement are not qualified.')
group('RTE FLOW','Authorized route/flow design plus native RIB/FIB, edge session policy and lifecycle writer','PARTIAL_CANDIDATE_NATIVE_SOURCE',['tools/route_audit.py','tools/route_record_review.py','terraform/modules/nsx-route/main.tf.json','terraform/modules/nutanix-route/main.tf.json','terraform/modules/openstack-route/main.tf.json'], 'Route models and exact native static-route resources do not implement a complete route authority, full flow compiler, expiration/teardown service, BGP ownership or effective NAT/PBR/session-revocation policy.')
group('IPAM','Authoritative address/name allocation and native DNS/DHCP lifecycle services','PARTIAL_DNS_EXTERNAL_IPAM_REQUIRED',['tools/dns_change.py','docs/DNS_LIFECYCLE.md'], 'The DNS client writes only exact accepted records. It does not allocate addresses, implement authoritative IPAM/DHCP, approve overlap, qualify server ACLs/propagation or release reuse tombstones.')
group('IPV6','Every offered native domain/edge/service/recovery path and local neighbour/control protocols','NATIVE_IMPLEMENTATION_AND_QUALIFICATION_OPEN',['tools/route_audit.py','lab/run_namespace_lab.py'], 'Offline IPv6 and loopback/AAAA tests are not native dual-stack. The packet fixture and native staging are IPv4; full IPv6 routing, local controls, PMTU and service/recovery dependencies remain unqualified.')
group('SVC ING EGR EXP','Service-facing endpoint, tenant-specific forward/reply boundary, ingress/egress owner and service resource authority','PARTIAL_FIXTURE_EXTERNAL_SERVICE_REQUIRED',['docs/engineering/TAD.md','lab/run_namespace_lab.py','tools/dns_change.py'], 'The local model demonstrates selected TCP/DNS paths, not a production ingress/egress, shared-service entitlement, revocation/expiry, TLS inspection, logging or permitted-return deployment.')
group('SITE PLACE CMP','Native scheduler eligibility, eligible host pools, HA admission and recovery target/data-location constraints','PARTIAL_VM_PREPARATION_ONLY',['terraform/modules/nutanix-workload/main.tf.json','terraform/modules/vsphere-workload/main.tf.json','terraform/modules/openstack-workload/main.tf.json'], 'VM preparation consumes accepted placement resources; it does not create/qualify host co-residency policy, evacuation/HA restrictions, independent sites, location agreements, guarantees or capacity under failure.')
group('STO LIFE','Storage/controller authorization, snapshot/clone/export lineage, retained copies, keys and media sanitization services','PARTIAL_RESOURCE_CREATION_EXTERNAL_LIFECYCLE',['terraform/modules/nutanix-workload/main.tf.json','terraform/modules/openstack-workload/main.tf.json','docs/DNS_LIFECYCLE.md'], 'Boot/data volume references and DNS retirement do not implement complete copy inventory, cross-owner export authorization, retention/hold policy, sanitization, receipt or safe shared-resource deletion.')
group('IAM CRY SEC','Enterprise IAM/PKI/KMS, consuming endpoint policy, session caches and independently controlled recovery custody','EXTERNAL_SECURITY_SERVICE_REQUIRED',['lab/mtls_fixture.py','docs/SERVICE_IDENTITY.md','tools/nsx_observe.py'], 'Temporary mTLS fixtures and verified client HTTPS are not enterprise authentication/authorization, revocation, FIPS/module approval, at-rest encryption, key custody, algorithm transition or native KMS outage qualification.')
group('IMG VULN','Approved image registry, artifact signature/digest policy and native guest/platform hardening configuration','EXTERNAL_IMAGE_AND_BASELINE_SERVICE_REQUIRED',['terraform/modules/nutanix-workload/main.tf.json','terraform/modules/vsphere-workload/main.tf.json','terraform/modules/openstack-workload/main.tf.json'], 'Modules consume image/template references; a governed image catalogue, provenance/revocation/hardening agents, vulnerability disposition and runtime guest compliance are not implemented.')
group('BKP REC','Backup management and data endpoints, protected-copy authority, catalogues/keys and isolated restore target','EXTERNAL_PROTECTION_SERVICE_REQUIRED',['docs/operations/README.md','sources/implementation_backlog.csv'], 'No complete native backup/KMS/catalogue integration, independent deletion control, measured application-consistent restore or retention-aware release is supplied.')
group('REL CAP SVCM FAIL','Service catalogue, measured surviving resource pools, security-edge and dependency failure/maintenance behaviour','EXTERNAL_CAPACITY_AND_QUALIFICATION_REQUIRED',['docs/engineering/TAD.md','lab/run_namespace_lab.py'], 'Illustrative capacity schedules and local link-failure fixtures do not establish measured production SLO/RTO/RPO, qualified limits, complete reservations or procured-to-available inventory.')
group('FAB EVPN','Physical leaf/spine/border configuration, provider route import/export, VTEP and multihoming control','NOT_IMPLEMENTED_IN_NATIVE_FABRIC_CODE',['docs/engineering/TAD.md','sources/implementation_backlog.csv'], 'No accepted switch/EVPN/MLAG/border implementation is part of these modules. Underlay addressing, management, measured interoperability, MTU and failures require the actual fabric engineering/build.')
group('PORT QUAL FUT','Qualified platform capability/eligibility record and representative native service/exit campaigns','DOCUMENTED_QUALIFICATION_NOT_EXECUTED',['docs/assurance/test-specifications.md','sources/implementation_backlog.csv'], 'No active authoritative qualified-platform record, bare-metal/container implementation or complete first/second-platform and exit evidence is supplied; unsupported capability must stay ineligible.')
group('API POL AUTO','Existing authorized service interface and scoped execution workflow before native side effects; native plan/readback layer','PARTIAL_OFFLINE_AND_SERVICE_CLIENT_CHECKS',['tools/input_review.py','tools/plan_review.py','tools/dns_change.py','tools/recovery_review.py'], 'These independent tools do not implement a complete catalogue/API, authoritative immutable status, quota/reservation, admission workflow or actual writer fencing. No bespoke controller is assumed necessary; an accepted existing interface can own those controls.')
group('TF','Terraform root/module source, plugin selection/locks and scoped backend use','CANDIDATE_CODE_ENGINE_GATE_REQUIRED',['tools/verify_terraform.py','terraform/modules/nsx-domain/main.tf.json','terraform/roots/nsx-domain/main.tf.json'], 'Source pattern and mocked plans do not prove native capabilities. Actual engine validation and reviewed dependency locks are required; credentials, modules/images and state backend have distinct trust boundaries.')
group('STATE','External remote-state backend, scoped execution identities and ownership handoffs','EXTERNAL_BACKEND_CONTROLS_REQUIRED',['terraform/roots/nsx-domain/main.tf.json','docs/INTERRUPTED_CHANGE_RECOVERY.md'], 'HTTP backend declarations do not implement encryption, access control, locking, versioned recovery or audit logs. Those backend controls and cross-owner grants must be configured and tested outside the source root.')
group('CICD DEP SUP','Protected Git review, dependency provenance, isolated runner, scoped apply approval and evidence capture','PARTIAL_REPOSITORY_WORKFLOW',['.github/workflows/validate.yml','tools/plan_review.py'], 'A read-only validation workflow is not an approved production runner, actual approval or native apply service. Action pins, dependency review, build images and signed source trust require ongoing ownership.')
group('DRIFT IR','Effective native runtime, incident owner and separately authorized current-generation recovery/repair process','PARTIAL_READBACK_REVIEW_NO_REPAIR',['tools/recovery_review.py','tools/nsx_observe.py','tools/nutanix_observe.py','tools/neutron_observe.py'], 'Exact-resource reads and offline decisions do not cover complete platform inventory, continuously detect all drift, authenticate incident authority, enforce real fencing or carry out safe native containment/repair.')
group('TEST EVID DEL','Approved qualification campaign, independent observation and evidence store at declared versions/topology','LOCAL_FIXTURES_NOT_NATIVE_QUALIFICATION',['docs/assurance/test-specifications.md','lab/run_readback_lab.py','lab/run_namespace_lab.py'], 'Reference procedures, local fixtures and hashes do not create native evidence, immutable evidence custody, complete assertion coverage, platform qualification or authorization.')
group('OBS','Independent collectors and audit paths at platforms, ZIPs, execution, identity and address authorities','EXTERNAL_TELEMETRY_SERVICE_REQUIRED',['docs/operations/README.md','lab/run_namespace_lab.py'], 'Fixture counters are not production telemetry. Stable event identifiers, collector independence, buffering/loss detection, storage retention/access and outage restrictions require native services and observations.')
group('MIG','Accepted temporary transfer interfaces, data-consistency/writer fencing and identity/DNS/route cutover','DOCUMENTED_TRANSITION_NATIVE_EXECUTION_OPEN',['tools/recovery_review.py','docs/DNS_LIFECYCLE.md'], 'Neither DNS changes nor readback performs complete cross-platform state transfer, native writer fencing, application consistency, reverse synchronization or transition teardown.')
group('NUT','Nutanix Prism/AOS/Flow native VPC, external attachment and mandatory category authority','PARTIAL_NATIVE_CANDIDATE_NOT_QUALIFIED',['terraform/modules/nutanix-domain/main.tf.json','terraform/modules/nutanix-route/main.tf.json','tools/nutanix_observe.py'], 'Exact installed AOS/Prism/Flow/API/provider/entitlement and route/selector/asynchronous behaviour remain unqualified; selected resources do not prove a complete ZIP or protected category authority.')
group('NSX','NSX manager/global-domain permissions, distributed and gateway rules, Tier-1/Tier-0/VRF and Edge forwarding','PARTIAL_NATIVE_CANDIDATE_NOT_QUALIFIED',['terraform/modules/nsx-domain/main.tf.json','terraform/modules/nsx-gateway-quarantine/main.tf.json','tools/nsx_observe.py'], 'No complete Tier-0/VRF/Edge foundation or applicable global/tenant rule inventory is deployed; aggregate realization is not effective policy, same-host isolation or native HA evidence.')
group('OS','OpenStack Keystone API policy, Neutron backend domain/router/ports and external-network authority','PARTIAL_NATIVE_CANDIDATE_NOT_QUALIFIED',['terraform/modules/openstack-domain/main.tf.json','terraform/modules/openstack-workload/main.tf.json','tools/neutron_observe.py'], 'Disabled ports/router and empty-group source is not the actual delegated-role proof, backend qualification, supported distribution/extensions or full stateful ZIP implementation.')
# Explicit facets preserve compound obligations rather than mislabelling one code
# pointer as their implementation. Each focus is a literal span in the requirement.
facets={
 'STATE-002':['encryption','strong authentication','locking','recovery/versioning','access logging','separation'],
 'CRY-001':['at rest','in transit','algorithms/modes','endpoint identity validation','module/operating-environment evidence','exceptions'],
 'CRY-002':['Key use','administration','recovery','destruction','retained-data recovery'],
 'IAM-001':['Human','workload','automation identities','role or group inheritance'],
 'MGT-004':['controlled','strongly authenticated','logged','time-bounded','tested'],
 'CMP-001':['Compute placement','maintenance evacuation','migration','HA restart','co-residency matrix'],
 'STO-001':['owner','categorization','access scope','key policy','placement/retention constraints','lineage','cross-scope attachment or export'],
 'BKP-003':['consistency','retention','location','key','protected-copy requirements','successful isolated restore'],
 'BKP-004':['Production credentials','independent/immutable','keys and catalogue'],
 'REL-001':['measurement scope','SLO','failure tolerance','maintenance treatment','RTO/RPO','consistency','dependencies','test cadence'],
 'PLACE-002':['Data','backup','telemetry','diagnostic','control-plane','administrative-access','key locations/control constraints'],
 'FAB-004':['addressing/routing authority','control-plane protection','MTU','fault convergence','management isolation','maintenance','measured scale'],
 'EVPN-002':['split-brain','link/peer failure','MTU','route withdrawal','stateful-path behavior'],
 'ZIP-006':['two zone authorities','joint approval','required security functions','management authority','heightened posture','session-revocation behavior','current evidence'],
 'SVC-003':['direction','endpoint identity','authentication','allowed scope','availability','failure behavior','management separation','revoked'],
 'AUTO-002':['journaled','idempotent','eligible capacity/addresses','deny before attachment/exposure','current-generation evidence','authorization'],
 'API-003':['immutable IDs','idempotent create','optimistic concurrency','typed/closed schemas','authorized references','authoritative service-owned status'],
 'RTE-004':['connected routes','recursive next hops','summaries','NAT/PBR interactions','all enabled address families','realized forwarding'],
 'LIFE-002':['live-service removal','retained-data obligations','identity','DNS','route','policy','attachment','copy','key lifecycle'],
 'MIG-003':['data/application consistency','identity/key dependencies','equivalent security outcomes','fencing/cutover','rollback feasibility','transition teardown'],
 'DOC-001':['stable identifier','accountable owner','applicability','source basis','verification procedure','exception policy'],
 'QUAL-001':['product/API/provider/hardware tuple','features/licenses','tested limits','evidence','approval'],
}
alloc=[]
for req in reqs:
 ident=req['requirementId'];family=ident.split('-')[0]
 if family not in profiles:raise ValueError('Missing explicit family allocation '+family)
 locus,disposition,artifacts,gap=profiles[family]
 for p in artifacts:
  if not (R/p).exists():raise ValueError('Missing concrete artifact '+p)
 focus=facets.get(ident)
 if not focus:
  # Preserve meaningful semicolon-separated clauses as separate coverage units.
  focus=[x.strip() for x in req['text'].split(';') if x.strip()]
 for i,phrase in enumerate(focus,1):
  if phrase not in req['text']:raise ValueError((ident,phrase))
  alloc.append({'assertion_id':f'{ident}/A{i:02d}','requirement_id':ident,'source_requirement':req['text'],
   'assertion_focus':phrase,'focus_semantics':'Exact source span under the complete requirement; not a replacement normative statement',
   'source_sections':req['parentSections'],'responsible_role':req['ownerRole'],
   'enforcement_location':locus,'implementation_disposition':disposition,'artifacts':artifacts,
   'required_configuration':'Site engineering must name the actual native object/role/service and its accepted settings for: '+phrase,
   'verification_procedures':[x.strip() for x in req['baselineTests'].split(';') if x.strip()],
   'verification_method':'Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.',
   'evidence_level':'SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED',
   'observed_native_evidence':[],'remaining_dependency':gap,'applicability':'TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA',
   'allocation_status':'PROPOSED_ENGINEERING_ALLOCATION_NOT_CONTROL_SATISFACTION'})
(S/'implementation_allocation.json').write_text(json.dumps(alloc,ensure_ascii=False,indent=2)+'\n')
with (S/'implementation_allocation.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=list(alloc[0]),lineterminator='\n');w.writeheader()
 for a in alloc:w.writerow({k:'; '.join(v) if isinstance(v,list) else v for k,v in a.items()})
# Historical finding disposition is deliberately not an invented closure.
audit=S/'completion-audit-original'
historical=read(audit/'historical_audit_dispositions.csv')
for a in historical:
 a['accountable_role']='Architecture authority and platform assurance owner' if int(a['original_finding'][1:])<13 else 'Engineering / lifecycle assurance owner'
 a['current_scope_reference']='docs/assurance/implementation-allocation.md'
 a['required_closure_evidence']='Assigned owner applicability decision, implemented control or accepted scope disposition, independently reviewed current-version observation and actual closure authority.'
 a['remediation_release_status']='INDIVIDUALLY_TRIAGED_NOT_CLOSED'
(S/'historical_findings.json').write_text(json.dumps(historical,ensure_ascii=False,indent=2)+'\n')
# Full source test data, no status promotion.
base=R/'reference/Portable_Hosting_Delivery_Kits_v1_1'
family={
 'CT':{'source':str((shared/'tests.csv').relative_to(R)),'records':read(shared/'tests.csv')},
 'RA':{'source':str((base/'05_Reference_v1_4/registers/realization_verification_addenda.json').relative_to(R)), 'records':json.loads((base/'05_Reference_v1_4/registers/realization_verification_addenda.json').read_text())},
 'W14':{'source':str((base/'05_Reference_v1_4/registers/v1_4_verification_assertions.csv').relative_to(R)),'records':read(base/'05_Reference_v1_4/registers/v1_4_verification_assertions.csv')},
 'Q11':{'source':str((shared/'development/qualification_observation_cards.csv').relative_to(R)),'records':read(shared/'development/qualification_observation_cards.csv')},
}
(S/'verification_families.json').write_text(json.dumps(family,ensure_ascii=False,indent=2)+'\n')
print('Seeded proposed assertion allocation and copied verification-family records; no native acceptance claimed.')
