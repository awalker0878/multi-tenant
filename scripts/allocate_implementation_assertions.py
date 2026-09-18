#!/usr/bin/env python3
"""Initial proposed assertion allocation from frozen requirements; not control acceptance.

Run only explicitly in a new correction workspace. Existing allocation records are
never overwritten; later actual owner/evidence updates require review, not regeneration.
"""
from pathlib import Path
import csv,json,re,sys
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));from build_documentation import Builder
if '--write-initial-allocation' not in sys.argv:
 raise SystemExit('Explicit --write-initial-allocation required; writes proposed records only')
if (R/'sources/assurance/implementation_assertions.json').exists():
 raise SystemExit('Existing allocation retained; review changes instead of regenerating it')
b=Builder(R);req=list(csv.DictReader((R/'reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/requirements.csv').open(encoding='utf-8-sig')))
# Family allocation is a real boundary/disposition, not an invented deployed enforcement mechanism.
def profile(f):
 if f in {'MGT','STATE','SEC','IAM','CRY'}:
  return ('EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED','Approved management/IAM/key/state service and privileged execution boundaries',['docs/current/TAD-infrastructure.md','docs/current/interface-agreements.md'],'Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records','Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case.','Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.')
 if f in {'ZIP','EDGE','ING','EGR','ZONE','MICRO','OVL','RTE','TEN','SDI'}:
  return ('CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED','Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge',['terraform/modules','tools/route_audit.py','docs/NATIVE_READBACK.md'],'Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides','Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure.','A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.')
 if f in {'NUT','NSX','OS'}:
  mod={'NUT':'nutanix-domain','NSX':'nsx-domain','OS':'openstack-domain'}[f]
  obs={'NUT':'nutanix_observe.py','NSX':'nsx_observe.py','OS':'neutron_observe.py'}[f]
  return ('CANDIDATE_PARTIAL_VENDOR_REALIZATION','Actual selected product/API/backend and mandatory provider-owned resource policy',[f'terraform/modules/{mod}',f'tools/{obs}','docs/current/TAD-infrastructure.md'],'Selected supported native version tuple, scoped privilege definitions and exact build artifacts; actual effective-state evidence','Exercise the applicable vendor CT/RA addendum using real delegated identities, native state and positive/negative/failure data paths.','Local API fixtures and mock plans do not qualify the installed hypervisor/backend or complete management/edge/Flow/DFW policies.')
 if f in {'IPAM','DNS','SVC'}:
  return ('EXTERNAL_AUTHORITATIVE_SERVICE_WITH_CANDIDATE_DNS_INTEGRATION','Authoritative IPAM/name registry and explicitly scoped provider service endpoints',['tools/dns_change.py','docs/DNS_LIFECYCLE.md','docs/current/interface-agreements.md'],'Accepted service binding, resource entitlement, authoritative allocation/TTL/retention record and native API/transport ACL','Observe exact permitted resource/operation and denied foreign/admin access; verify each origin-specific reply, lifecycle and service-loss behaviour.','The DNS client is not an IPAM allocator or production DNS authority; actual server ACLs, secondary/cache propagation and other service integrations remain required.')
 if f in {'CMP','PLACE','STO','BKP','IMG','DATA'}:
  return ('EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE','Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate',['terraform/modules/nutanix-workload','terraform/modules/vsphere-workload','terraform/modules/openstack-workload','docs/current/TAD-infrastructure.md'],'Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures','Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies.','VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.')
 if f in {'FAB','EVPN','IPV6','SITE','NET','MTU'}:
  return ('EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED','Physical/overlay transport, site routing, OOB and actual address-family paths',['docs/current/TAD-infrastructure.md','docs/current/interface-agreements.md','tools/route_audit.py'],'Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner','Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure.','Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.')
 if f in {'TF','AUTO','CICD','DRIFT','API'}:
  return ('CANDIDATE_PARTIAL_TOOLING_AND_EXTERNAL_EXECUTION_GOVERNANCE','Scoped execution runner, authoritative source/state, native resource writer and change/evidence system',['terraform/roots','tools/verify_terraform.py','tools/recovery_review.py','docs/INTERRUPTED_CHANGE_RECOVERY.md'],'Immutable reviewed artifact/input/state/approval records, scoped credentials and actual authoritative native writer/fencing mechanism','Review exact source and current state; execute accepted operation/uncertainty/containment tests without treating a local status as authority.','Tool helpers do not supply authentic approvals, actual fencing, whole-platform admission, signed artifact custody or authorized apply.')
 if f in {'OBS','CAP','FAIL','REC','VULN','IR','LIFE','MIG','OPS','SVCM','SUP'}:
  return ('EXTERNAL_OPERATING_SERVICE_OR_CONTROL_REQUIRED','Actual operational service, independent telemetry, capacity/failure domains and lifecycle authorities',['docs/current/transition-and-as-built.md','docs/current/TAD-infrastructure.md','sources/implementation_backlog.csv'],'Owned runbook/service configuration, measured limits, dependency inventory and actual incident/recovery/retention acceptance record','Perform each documented assertion on the actual approved service using independent observations and measured time/data outcomes; inspect exact versions and residual risks.','Reference procedures and local fixtures do not provide the selected operational infrastructure, measured recovery/HA, native supply-chain response or disposition authority.')
 return ('MANUAL_GOVERNANCE_OR_EXTERNAL_AUTHORITATIVE_RECORD_REQUIRED','Architecture/design review and separately governed service/adoption/qualification authority',['docs/current/RAD-adoption.md','docs/current/TAD-infrastructure.md','docs/assurance/verification-families.md'],'Scope-specific current architecture/engineering/authority record addressing the exact assertion, with named owner and protected evidence','Review the actual versioned record and its individual assertions; corroborate implementation-specific obligations with the applicable native tests.','No controller or document generator can issue organizational approval, assess all adopted controls or complete absent site-specific evidence.')
# Explicit, separately observable facets in compound obligations; source umbrella retained in all cases.
facets={
 'ARCH-001':['Consumer contract is vendor neutral','Consumer does not need native IDs','Consumer does not need vendor-specific topology objects'],
 'ARCH-003':['Every inter-zone path is explicitly identified','Each identified inter-zone path traverses its applicable qualified boundary'],
 'ARCH-004':['Workload-to-management route and policy separation','Authorized privileged access paths','OOB transport and recovery dependencies separately documented'],
 'INV-001':['Tenant ownership identity is separate','Zone semantics are separate','Workload lifecycle identity is separate','Native realization identity is separate'],
 'INV-006':['Native realized resources observed','Effective required security controls verified','Service-ready promotion held until both complete'],
 'INV-007':['Admission dependency loss halts new changes','Control-plane loss does not create an implicit allow'],
 'DOC-001':['Stable requirement identifier','Accountable owner','Applicability','Source basis and edition','Verification procedure for each assertion','Exception policy','Complete generated active catalogue'],
 'CAT-001':['Confidentiality impact','Integrity impact','Availability impact','Exact security profile','Exact assurance profile','Exact availability profile','Exact recovery profile','Exact placement profile'],
 'MODEL-001':['Network has one native domain instance','Network resolves to logical domain','Network resolves to zone class','Network resolves to address authority','Accountable owner','Shared-domain dependencies explicitly recorded'],
 'MODEL-002':['Service-consumption boundary','Platform-control boundary','Privileged-management boundary','OOB transport dependency','No implicit cross-plane authority'],
 'TEN-002':['Tenant cannot mutate provider management','Tenant cannot mutate security-edge infrastructure','Tenant cannot mutate fabric','Tenant cannot mutate another tenant'],
 'WSD-003':['Compute dependency','Storage dependency','Identity dependency','Backup dependency','Recovery dependency','Exposure dependency','Evidence dependency','Unresolved mandatory dependency holds readiness'],
 'ZIP-005':['Separate data-path security service','Separate management-path security service','Shared virtualization is covered by actual assurance analysis'],
 'ZIP-006':['Exactly the adjacent zone authorities','Joint approval','Required security functions','Management authority','Heightened posture','Existing-session withdrawal behaviour','Current attributable evidence'],
 'MGT-004':['Separate emergency authority','Strong emergency authentication','Emergency access logging','Bounded access where feasible','Periodic actual recovery exercise'],
 'MGT-005':['MZ security semantics','Physical/logical OOB dependencies','Remote-management boundary','Privileged identity control','Tenant-facing interface excludes infrastructure administration'],
 'RTE-003':['Route purpose and bounded scope','Approval','Expiry','Telemetry','Teardown of expired transitional path'],
 'RTE-004':['Native connected routes','Recursive next-hop resolution','Summaries','NAT interaction','Policy-based routing interaction','Every offered address family','Realized forwarding agrees with approved topology before exposure'],
 'IPAM-004':['Allocation authority and delegated scope','Address lifecycle reconciled with native resource','DNS and address state reconciled','No orphan release or duplicate allocation'],
 'STATE-001':['Foundation writer isolated from tenant writer','Management writer isolated','Security-edge writer isolated','Tenant/workload writer cannot span all authorities'],
 'STATE-002':['Backend encryption','Strong authentication','Exclusive locking','Version/history recovery','Access logging','Sensitivity-appropriate authority separation'],
 'STATE-003':['Journaled dependency workflow','Minimal scoped outputs','Idempotent stage completion','Data-safe compensation','State-file restoration is not infrastructure rollback'],
 'TF-002':['Declared provider constraints','Real root lockfile selections and checksums','Lock reviewed and version controlled'],
 'TF-005':['Immutable module version/source pin','Immutable runner image pin','Accepted package checksums','Provenance verified before privileged execution'],
 'CICD-002':['Approval binds immutable plan','Input/profile/policy hashes bound','Current state/dependency generation bound','Stale or changed approval refused','Expired approval refused'],
 'SEC-003':['Actual credential rotation','Revocation','Break-glass recovery exercise'],
 'ASSUR-002':['Compute isolation scope','Storage isolation scope','Routing isolation scope','Edge sharing/isolation scope','Management isolation scope','Backup authority scope','Key custody scope','Measurable test and exception rules'],
 'EVID-001':['Source revision','Policy version','Provider and module version','Actual security relationships','Test observations','Active exception references'],
 'EVID-002':['Target generation','Source/profile/capability/dependency hashes','Artifact integrity','Collection timestamp','Actual test executions','Active exception scope','Freshness after material change'],
 'OBS-003':['Event coverage','Tenant/domain attribution','Time integrity','Data minimization','Forwarding latency','Buffering','Loss alerting','Retention','Access control','Secure behaviour during collection failure'],
 'CAP-002':['Measured surviving capacity','Enabled security overhead','Shared dependency bottlenecks','Quota/entitlement separation','Operational reserve','Actual approved failure model'],
 'CAP-003':['Procured capacity','Received capacity','Commissioned capacity','Allocated capacity','Reserved capacity','Consumed capacity','Unused-capacity age/constraint/owner remediation'],
 'FAIL-003':['Loss/partition behaviour of each critical dependency','Credential and key continuity','Logging loss response','State recovery','Split-brain prevention','Unavailable authority does not permit bypass'],
 'REC-001':['Independent bootstrap access','Protected key recovery','Protected state recovery','Protected catalogue recovery','Dependency order','Actual writer fencing','Isolated validation','Attributable activation authority'],
 'REC-002':['Measured service RTO','Measured service RPO','Data consistency','Security outcomes','Temporary route removal','Temporary grant/exposure removal'],
 'IR-002':['Incident decision authority','Scoped containment','Evidence custody','Owner coordination','Recovery acceptance','Emergency change reconciliation','Explicit attributable containment release'],
 'LIFE-002':['Live service removal separate from retention','Identity retirement','DNS retirement','Route retirement','Policy retirement','Attachment cleanup','Retained copies have an owner','Key lifecycle preserved','Shared or held resources not deleted'],
 'MIG-003':['Data/application consistency','Identity dependencies','Key dependencies','Equivalent security outcomes','Writer fencing and cutover','Rollback feasibility after target writes','Complete temporary access teardown'],
 'OPS-002':['Owner and escalation record','Dependency inventory','SLO and recovery acceptance','Capacity record','Monitoring coverage','Actual runbooks','Support and version record','Current evidence','Privileged access matches real authority'],
 'EXC-003':['Requirement IDs','Precise scope','Effective/expiry times','Compensating controls','Authorized risk approval','Evidence preservation at expiry','Pre-approved secure continuity/remediation'],
}
rows=[]
for requirement in req:
 id=requirement['requirementId'];family=id.split('-')[0];disposition,location,artifacts,record,method,remaining=profile(family)
 for artifact in artifacts:assert (R/artifact).exists() or artifact=='docs/assurance/verification-families.md',artifact
 # The full obligation remains alongside explicitly decomposed facets. Semicolon clauses
 # provide a minimal independent branch even for a requirement not enumerated above.
 statements=['Complete source obligation; all applicable clauses must be satisfied: '+requirement['text']]
 statements+=facets.get(id, [x.strip() for x in requirement['text'].split(';') if x.strip()] if ';' in requirement['text'] else [])
 for number,assertion in enumerate(statements,1):
  rows.append({'assertion_id':f'{id}.A{number:02d}','requirement_id':id,'source_requirement':requirement['text'],
    'assertion':assertion,'implementation_owner':requirement['ownerRole'],'enforcement_location':location,
    'implementation_disposition':disposition,'required_artifact_or_record':record+' — specifically: '+assertion,
    'candidate_artifacts':artifacts,'verification_method':method,'reference_tests':[x.strip() for x in requirement['baselineTests'].split(';')],
    'evidence_class':'NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction',
    'remaining_dependency':remaining,'owner_review':'PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending',
    'source_sections':requirement['parentSections'],'not_applicable':'Not selected; explicit scope rationale and authority required before any N/A disposition'})
out=R/'sources/assurance';out.mkdir(exist_ok=True)
(out/'implementation_assertions.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
with (out/'implementation_assertions.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
 for row in rows:w.writerow({k:'; '.join(v) if isinstance(v,list) else v for k,v in row.items()})
print(len(req),'requirements',len(rows),'assertion/obligation allocations')
