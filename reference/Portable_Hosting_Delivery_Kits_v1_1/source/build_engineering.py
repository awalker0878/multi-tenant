from doc_engine import Book
from catalogue import DATA

def build_ek():
 b=Book('EK');heads=[(1,'Engineering work plan and release boundary'),(2,'Site, equipment and physical foundation'),(3,'Addressing, routing, policy and attachment schedules'),(4,'Compute, storage and protected data'),(5,'Management and shared-service interfaces'),(6,'Capacity, MTU, performance and failure analysis'),(7,'Supported stack and provisioning operation coverage'),(8,'Build, test and implementation handoff')]
 b.front('Turn approved architecture into a design an implementation team can execute without guessing.', 'Use Engineering_Schedules.xlsx for working schedules and calculations, ET for the controlled design and review, and VC for native realization decisions. Keep example route and capacity sheets separate from actual site schedules.',heads)
 b.page(1,heads[0][1], 'Engineering supplies exact parameters, native resource choices, compatibility evidence and reproducible build/verification instructions. It does not silently change the approved sharing model or service promise.', [('RA',30),('QUAL',2),('ET',1)])
 b.table(['Engineering output','Required inputs','Buildable when'],[
 ('Site and physical plan','Adopted site/cell scope, inventory, facility protections and failure model.','Every device/link has a role, endpoint, owner and supported configuration basis.'),
 ('Logical/network/security plan','Domains, service flows, ZIP decisions and family requirements.','Every next hop, return path, enforcement point and rejected alternative is explainable.'),
 ('Resource/service plan','Compute/data classes, identity/key/protection and recovery constraints.','Actual pool/backend/role/copy membership and measured capacities are explicit.'),
 ('Tool and lifecycle plan','Exact products/APIs/providers and native installation ownership.','All required lifecycle operations have supported ownership and failure treatment.'),
 ('Release/test pack','Current LLD, artifacts, MOP, test scope and expected outcomes.','Implementers can execute controlled steps and capture the required observations.')],[1.70,2.74,2.70])
 b.p('Use EK-01–EK-09 as deliverable IDs. The actual site configuration, bill of materials and command/API artifacts are produced from approved values, never from documentation addresses. Unresolved site values remain explicit blockers at their relevant stage.')
 b.note('Engineering release is not platform qualification. A supported design still needs actual build results, boundary tests, performance and recovery evidence.')
 b.page(2,heads[1][1], 'The physical design supplies the inventory behind the logical diagrams. Shared power, rack, uplink, storage or management dependencies must be visible before redundancy is claimed.', [('RA',3),('RA',4),('RA',5),('ET',2)])
 b.table(['Schedule','Required fields / engineering checks'],[
 ('Equipment and bill of materials','Asset role, model/quantity, CPU/memory/storage/NIC, firmware, rails/optics/cables, support/entitlement, spare policy and procurement assumption.'),
 ('Rack and facility allocation','Rack/U position, power-feed assignment, load/cooling capacity, access restrictions, dependency group and facility acceptance reference.'),
 ('Ports and cables','Link ID; both devices and ports; medium/speed/length; optic compatibility; host team or LAG; VLAN/transport role; labeling and test record.'),
 ('Fabric and borders','Topology, loopbacks/link addresses, ASNs, neighbour/import/export policy, ECMP, optional EVPN RD/RT/VNI authority and external handoff.'),
 ('OOB and management','Independent access path, actual switches/interfaces, permitted targets, privileged path and recovery dependency.'),
 ('Staging and support','Trusted firmware/images, secured initial configuration, asset matching, diagnostic handling and manufacturer-specific install/replacement method.')],[1.74,5.40])
 b.p('Choose qualified MLAG, EVPN multihoming or another supported host attachment pattern. Document peer-link/keepalive or Ethernet-segment behaviour, orphan endpoints, split-brain containment and supported drain/reload order. Do not equate matching feature names with interoperability.')
 b.p('Physical installation and electrical/facility work are performed by qualified personnel following site and manufacturer procedures. This kit records approvals, labels and acceptance; it does not replace lifting, electrical, optical or equipment safety instructions.')
 b.page(3,heads[2][1], 'Keep three records distinct: address ownership, routing reachability and permitted communication. A correct prefix allocation does not prove a correct route, and a route does not authorize a flow.', [('NET',1),('NET',3),('NET',4),('WD',6),('ET',3)])
 b.table(['Record','What the implementer must receive'],[
 ('Network and domain schedule','Owner, zone/domain instance, native context, family mode, actual prefix/gateway, IPAM authority and DHCP/DNS policy.'),
 ('Route schedule','Routing owner, family, destination, next hop and egress interface, import/export origin, related boundary, return-route owner and prohibited alternatives.'),
 ('Flow schedule','Initiator and target identity, protocol/service operation, port/type detail as needed, authentication, encryption, stateful replies, log policy and expiry.'),
 ('Attachment inventory','Domain-to-edge and edge-to-service units separately counted; physical members and HA overhead additional; reuse/quarantine rules.'),
 ('Boundary design','Every required ZIP function located; policy precedence, shared connected routes, native distributed routing, NAT/PBR and fault paths analyzed.'),
 ('Service reply design','Origin-specific return routing or a supported mediation pattern; no broad default masking asymmetric enforcement.')],[1.66,5.48])
 b.p('Record IPv4-only, IPv6-only or dual-stack as an offered capability. Include neighbour/discovery and required ICMPv6/PMTU behaviour, source validation, DNS transport and recovery paths for every enabled family. The WD address ranges remain documentation examples only.')
 b.note('Review by walking an allowed request and reply, unsolicited reverse initiation, same-domain traffic and a cross-tenant denial. Inspect actual forwarding candidates; a failed ping from a dead endpoint is not proof.')
 b.page(4,heads[3][1], 'Bind resources to the approved isolation and failure scopes before sizing or placement. Include maintenance evacuation, restart and restore, not only initial VM creation.', [('RA',11),('RA',12),('WD',7),('ET',5)])
 b.table(['Layer','Detailed engineering content'],[
 ('Host pools','Actual eligible hosts/clusters, zone/domain sharing, hardware/CPU compatibility, reservations, scheduling/anti-affinity and restart constraints.'),
 ('VM/image profile','Approved template/image digest, guest OS/driver/tooling, boot mode, vCPU/memory, virtual devices, management and guest configuration owner.'),
 ('Virtual disks','Owned volume/backing policy, attachment authority, encryption/key context, performance class and snapshots/clone restrictions.'),
 ('Guest data services','Selected block/file/object protocol, tenant namespace/ACL/policy, endpoint, credential scope, quotas and access-path control.'),
 ('Backend data movement','Replication/rebuild membership, latency/loss limits, failure reserve, encryption as required and management boundaries.'),
 ('Protected copies','Capture consistency, schedule/retention/hold, independent administration, catalogue/key location, restore path and disposal.')],[1.64,5.50])
 b.p('Do not add backend replication or hypervisor key access to the guest firewall permit list. A virtual-disk read can be mediated by the hypervisor/storage stack without using the guest NIC. A file/object client inside the guest uses its approved network and data-service authorization path.')
 b.p('Calculate usable storage with the selected protection layout, growth, snapshots and rebuild headroom. Do not equate provisioned virtual capacity, physical used capacity, replicas and backups. Record how the chosen service behaves during contention and degraded operation.')
 b.page(5,heads[4][1], 'Every shared service needs a consumption interface, an administrative interface, an authorization model and a recovery dependency. Record the actual client; it may be a host, service appliance, data mover or workload.', [('SVC',1),('SVC',2),('SVC',3),('ET',6)])
 b.table(['Service / plane','Design and ownership inputs'],[
 ('Management and OOB','Hardened privileged origin, boundary path, roles, targets, MFA/PAM requirements, logs, emergency recovery and supplier sessions.'),
 ('IPAM/DNS/DHCP','Authoritative or delegated scope, reservation/release ownership, forward/reverse zones, resolver endpoints, leases/TTLs and reuse quarantine.'),
 ('Time and logging','Approved time source, skew treatment; authenticated ingestion/collection, event identity, buffering, loss detection and retention/access.'),
 ('Identity/PKI/KMS','Issuers/trust roots, service/client identities, role mapping, certificate renewal/revocation, key use/admin/recovery separation and cached/outage behaviour.'),
 ('Backup and software supply','Capture API and transfer path; protected repository/catalogue; trusted images/packages and update source; publication versus retrieval authority.'),
 ('Bootstrap transition','Temporary service location, permitted scope, owner/expiry, steady-state migration and independent recovery retained after cleanup.')],[1.67,5.47])
 b.p('Define exact protocol configurations against the adopted security profile and applicable source editions. ITSP.40.062 is protocol-configuration guidance; use it with the selected algorithms and actual product modes rather than assuming an encryption checkbox proves a safe channel. [K10]')
 b.external(['K10']);b.note('A service handoff must include failure behaviour and operational ownership. “Another team will configure it later” is not an accepted dependency.')
 b.page(6,heads[5][1], 'The engineering workbook contains labelled calculators and a separate worked fixture. Inputs are editable; derived values are formulas. Unknown real capacity remains unknown rather than silently becoming zero or a guessed safe default.', [('QUAL',3),('WD',11),('NET',5),('ET',7)])
 b.table(['Calculation','Basis and review requirement'],[
 ('Surviving service capacity','Measured sustainable capacity remaining after the covered failure, minus operational reserve and existing committed demand. Test all limiting units independently.'),
 ('New demand','Workload plus required temporary test resources and provider overhead. Account for existing commitment once; do not add usage already included in that commitment.'),
 ('Headroom and growth','New demand must fit every applicable bottleneck. Record lead time and forecast trigger; a free host cannot compensate for exhausted inspected sessions.'),
 ('Storage','Capacity/performance under protection overhead, rebuild, copies and retention; specify raw versus usable units and evidence.'),
 ('MTU','Workload packet plus actual inner framing, encapsulation, outer headers and options; compare against the smallest active/surviving path limit.'),
 ('Recovery timing','RTO dependency sequence and decision/cutover time; RPO from the recoverable consistency point; constraints remain enforced.')],[1.70,5.44])
 b.p('The WD fixture has four permanent endpoints and one sequential temporary probe: 10 vCPU, 20 GiB guest memory and 400 GiB requested virtual disks at peak. These are not host minima or physical-storage totals. Provider, edge, management, copies and failure reserves are additional.')
 b.p('The basic VXLAN arithmetic in WD is one encapsulation case, not a universal tunnel allowance. Record inner tags, outer family, Geneve/options, IPsec or nested encapsulation separately. Link-frame MTU and outer-IP MTU may be reported differently by products.')
 b.page(7,heads[6][1], 'Use one support record for the exact installed combination and a separate operation matrix for what the tools can actually manage. Documentation availability is not measured qualification.', [('VND',7),('PROV',3),('VC',7),('ET',8)])
 b.table(['Support dimension','Evidence to capture'],[
 ('Installed tuple','Hardware/NIC/firmware, OS/hypervisor, managers, network backend, storage/protection, APIs, provider/installer versions and enabled entitlements.'),
 ('Operation coverage','Observe, create, update, adopt/import, replace, delete and discover uncertain outcome per native resource family.'),
 ('Single writer','Exactly which tool/team owns the native object and any independently managed subresource; protected handoff boundaries.'),
 ('Lifecycle semantics','Asynchronous completion, retry/discovery, replacement/destruction, upgrade/rollback constraints and cleanup.'),
 ('Reproducibility','Trusted package provenance, reviewed provider lock, separately fixed module/runner versions, artifact integrity and controlled credentials.'),
 ('Unsupported case','Supported native alternative with owner/evidence, or excluded capability. No shim or empty root is called complete provisioning.')],[1.70,5.44])
 b.p('HashiCorp documents provider configurations and inheritance within modules, while provider dependency locks do not lock remote module versions. Keep those controls separate in the engineering release. [K03, K04]')
 b.external(['K03','K04'])
 b.page(8,heads[7][1], 'The implementation team must receive both how to change the environment and how to determine whether the change succeeded safely. The expected observation is part of every material step.', [('PROV',4),('PROV',5),('QUAL',5),('ET',9),('IT',1)])
 b.table(['Release item','Required content'],[
 ('Controlled design','HLD/LLD revision, accepted decisions, actual schedules, diagrams, scope and unresolved blockers.'),
 ('Build artifacts','Configuration/module/installer inputs, checksums, exact tool versions, credential references and ownership.'),
 ('Method of procedure','Prerequisites, actual target, action, expected observation, timeout, safe stop, operator and evidence receipt per step.'),
 ('Recovery of change','Rollback eligibility, irreversible/data-changing points, forward repair, outstanding task discovery and restart authority.'),
 ('Qualification design','Applicable requirements/assertions, healthy controls, test topology, families, failure/load scenarios, evidence and review method.'),
 ('Activation and handover','Initial G4 obligations, valid authority, current checks, reversible exposure, post-change observation and as-built records.')],[1.65,5.49])
 b.p('Walk the MOP with operations before the window. Ensure a test-only fixture cannot accidentally carry production data. Confirm spare test capacity and restore material. Review brownfield plans for unintentional replacements and remove dual ownership before mutation.')
 b.note('Engineering handoff is complete only when a named implementation owner can identify every required input and safe stop. No unknown native command, route or privileged credential is supplied by assumption.')
 b.save()

def build_et():
 b=Book('ET');heads=[(1,'Design identity, scope and baseline'),(2,'Physical inventory, facility and port schedule'),(3,'Networks, addresses and native gateways'),(4,'Routes, ZIPs and permitted flows'),(5,'Compute, storage and placement'),(6,'Management, services and trust'),(7,'Capacity, MTU and failure calculations'),(8,'Exact platform and tool operation coverage'),(9,'Build and qualification design'),(10,'Engineering review and controlled handoff')]
 b.front('Editable site-specific low-level design. Link to controlled schedules, not duplicated guesses.', 'Use the response fields to assemble a named design. Engineering_Schedules.xlsx provides the detailed tabular records; identify its controlled revision here. Attach actual topology/connection drawings and product-specific artifacts after review.',heads)
 rows=[
 [('Design identity','Site/service ID, LLD version and author/reviewer roles.','ET_ID'),('Approved parent','HLD, G0 decision, reference version and accepted variations.','ET_PARENT'),('Scope and stages','New site, extension, adoption or tenant change; selected P0–P6 work.','ET_SCOPE'),('Controlled schedules','Workbook and artifact repository version/digest.','ET_SCHEDULES'),('Known constraints','Explicit unresolved site inputs, owners and blocked build scopes.','ET_GAPS'),('Release boundary','What is buildable now versus candidate or excluded.','ET_RELEASE')],
 [('Site/failure map','Actual rack/power/uplink/control/storage fault groups and facility evidence.','ET_SITE'),('Equipment/BOM','Model, quantity, support, firmware, capacity, optics and license references.','ET_BOM'),('Port/cable schedule','Both device/port endpoints, speed/media, role, label and redundancy.','ET_PORTS'),('Fabric topology','Leaf/spine or alternate, host attachment/multihoming and border design.','ET_FABRIC'),('Management/OOB','Actual independent interfaces, permitted targets and recovery path.','ET_OOB'),('Installation/staging','Approved qualified-personnel procedure, acceptance checks and shipment/asset receipt.','ET_STAGE')],
 [('Network register','Owner, zone/domain/instance, native object and offered families.','ET_NETWORKS'),('Actual allocations','Authoritative IPAM/delegation, prefixes, addresses, gateways and reservation IDs.','ET_IPAM'),('Underlay policy','ASNs, neighbours, import/export, authentication/control limits and convergence.','ET_UNDERLAY'),('Overlay/attachments','Tunnel transport, optional EVPN RD/RT/VNI ownership and isolated handoff capacity.','ET_OVERLAY'),('Name/host protocols','DNS/DHCP ownership, TTL/lease, IPv6 local controls and required PMTU treatment.','ET_PROTOCOLS'),('Release/reuse','Withdrawal, neighbour/session/DNS cleanup and quarantine before reuse.','ET_REUSE')],
 [('Boundary mapping','Logical ZIP endpoints/authorities to actual routing/enforcement components.','ET_ZIP'),('Forward/reply routes','Per-owner route/interface/next hop and return owner for each approved destination.','ET_ROUTES'),('Flow schedule','Source initiator, target, service/protocol, auth/TLS, stateful reply and logs.','ET_FLOWS'),('Bypass and precedence','Connected/native/distributed paths, imported routes, NAT/PBR, additive policies and extra NICs.','ET_BYPASS'),('Revocation/failure','Session termination/drain rule, enforcement failover and denied alternatives.','ET_REVOKE'),('Path evidence plan','Observation method and CT/W14 assertion for each required path.','ET_PATH_TEST')],
 [('Compute pools','Actual host eligibility, resource class and approved co-residency decision.','ET_COMPUTE'),('Scheduling/recovery','Placement, affinity, evacuation/HA restart, CPU/device compatibility and supported limits.','ET_SCHED'),('Images and guests','Image digest, boot/drivers/hardening and guest/application responsibilities.','ET_IMAGES'),('Storage class','Backend, disk/file/object identity, usable capacity/performance and authorization.','ET_STORAGE'),('Copy/key lineage','Snapshots, clones, replicas, encryption context, key use/custody and retention.','ET_COPIES'),('Protection/reuse','Capture/restore, independent repositories and approved media/key-scope sanitization.','ET_PROTECTION')],
 [('Privilege paths','Actual origin/boundary/target and scoped roles; recovery and supplier access.','ET_PRIVILEGE'),('Service endpoints','Actual client, endpoint/protocol, entitlement, return routing and management exclusion.','ET_SERVICES'),('DNS/time/telemetry','Authority, required transports, clocks, event identity, buffering, retention and access.','ET_TELEMETRY'),('Identity/PKI/KMS','Issuer/role, key-use/admin separation, rotation/revocation and loss behaviour.','ET_TRUST'),('Bootstrap transition','Temporary dependencies, owner/expiry and verified transfer to steady state.','ET_BOOTSTRAP'),('Dependency loss','Minimum survivors and blocked operations for service/control/key loss.','ET_DEPENDENCY')],
 [('Failure/load basis','Covered failure sets, simultaneous maintenance, workload mix and measurement conditions.','ET_LOAD'),('Capacity calculation','Measured survivor capacity, reserve, existing commitment, new demand and units.','ET_CAPACITY'),('Storage/performance','Protection/copy/rebuild overhead and latency/IOPS/throughput under contention.','ET_PERF'),('MTU budget','Per-path workload size, all headers/options/tags and smallest surviving limit.','ET_MTU'),('Recovery targets','Approved RTO/RPO and measurement boundaries; restore/failback method.','ET_RTO'),('Margins/expansion','Binding bottleneck, growth/lead time, trigger and assigned owner.','ET_GROWTH')],
 [('Exact tuple','Hardware/firmware/platform/control/backend/API/provider/installer with source evidence.','ET_TUPLE'),('Feature/entitlement','Actual enabled functions, licenses, limits and exclusions.','ET_FEATURES'),('Operation matrix','Observe/create/update/adopt/replace/delete/uncertain-outcome evidence per resource.','ET_OPERATIONS'),('Single-writer map','Owner/tool/state/subresource boundaries and accepted cross-team outputs.','ET_WRITERS'),('Artifact provenance','Provider lock, immutable module/runner/artifact references and protected credential source.','ET_PROVENANCE'),('Unsupported operation','Accepted native alternative, owner, observation/cleanup or excluded capability.','ET_ALTERNATIVE')],
 [('Method of procedure','Site-specific steps, targets, current prerequisites and expected results.','ET_MOP'),('Safe stop/recovery','Abort thresholds, rollback/data boundaries, forward repair and late-task discovery.','ET_ROLLBACK'),('Test campaign','Requirements/assertions, approved fixture, family/topology coverage and expected observations.','ET_TESTS'),('Test resources','Temporary probes, failure fixtures, load, spare capacity and safety/restoration plan.','ET_TEST_RES'),('Evidence handling','Capture method, sensitivity, integrity, retention and independent reviewer.','ET_EVIDENCE'),('Activation conditions','G2, applicable initial G4, current tenant checks and operating authority.','ET_ACTIVATE')],
 [('Review scope','LLD/workbook/artifacts version and stakeholders who reviewed them.','ET_REVIEW'),('Unresolved findings','Issue, owner, blocking gate and approved scope limits.','ET_FINDINGS'),('Controlled release','Actual engineering decision, authority/date/reference and artifact manifest.','ET_SIGNOFF'),('Implementation receipt','Named owner acknowledges usable design, inputs and safe-stop procedure.','ET_RECEIPT'),('Change impact','Other cells/services and required requalification if this design changes.','ET_IMPACT'),('As-built return','Who updates actual resource/configuration deviations and closes reconciliation.','ET_ASBUILT')]]
 refs=[[('RA',30),('AK',8)],[('RA',5),('NET',6)],[('NET',1),('NET',4)],[('NET',3),('WD',6)],[('RA',11),('RA',12)],[('RA',6),('SVC',3)],[('QUAL',3),('WD',11)],[('VND',7),('PROV',3)],[('PROV',4),('QUAL',5)],[('RA',30),('IK',1)]]
 for n,title in heads:
  b.page(n,title,'Actual site values are required. Complete the response fields and identify controlled schedule/diagram references. Unknown or unsupported items remain blocking for their affected scope.',refs[n-1]);b.inputs(rows[n-1])
  b.note('Review disposition: Draft until the actual engineering authority accepts the named scope. A checked form or calculator result does not establish live support, qualification or authorization.')
 b.save()

def build_vc():
 b=Book('VC');heads=[(1,'Common scope and native implementation contract'),(2,'Nutanix realization card'),(3,'VMware and NSX realization card'),(4,'OpenStack realization card'),(5,'Physical fabric and OOB realization card'),(6,'Shared services and security-edge realization card'),(7,'Support tuple, variations and evidence checklist')]
 b.front('A build track for each hosting stack and its shared foundations.', 'Use one card per selected realization. These cards state the native engineering decisions and build responsibilities; actual supported versions, settings, credentials and execution evidence must be entered in ET and the schedules.',heads)
 b.page(1,heads[0][1], 'The common WD fixture is the comparison baseline: tenant-01 and tenant-02, domains D01O/D01R/D02O/D02R, four permanent endpoints, two tenant boundary contexts and explicit shared-service handoffs. A temporary probe is needed for same-domain tests.', [('VND',1),('WD',2),('WD',11)])
 b.table(['Invariant','Native realization must show'],[
 ('Independent authority','Tenant administration, domain routing, mandatory policy and management scope are separate and enforced.'),
 ('ZIP-controlled transitions','All required forward/reply paths use qualified boundary functions; native paths do not silently bypass them.'),
 ('Shared-service consumption','Exact clients and endpoints, origin-specific reply, backend entitlement and administrative exclusion.'),
 ('Resource eligibility','Compute, storage, copies and recovery remain inside approved sharing/location boundaries.'),
 ('Lifecycle ownership','Install/commission, allocate, update, adopt, replace, delete and interrupted-operation repair have one owner.'),
 ('Equivalent outcome','Same acceptance semantics and observed evidence, not matching native IDs or identical topology.')],[1.69,5.45])
 b.p('Do not install three stacks just to make the first stack qualify. Prove one controlled realization, then repeat the required comparison and representative image/data recovery on a second target. Treat a composite cross-stack WSD as an explicit additional design.')
 b.note('Common prerequisites: adopted design; approved test scope; actual platform tuple; accepted foundation and required bootstrap; scoped identities; capacity and restore material; current native configuration artifacts.')
 b.page(2,heads[1][1], 'Reference mapping: AHV/AOS with protected Prism/Flow administration, separate domain routing contexts, protected endpoint policy and independently owned edge and shared-service integrations.', [('RA',16),('VND',3),('WD',8)])
 b.table(['Build concern','Specific engineering decision / receipt'],[
 ('Installation and management','Selected supported cluster/Prism/Flow installation, exact component releases, management path, cluster health and recovery dependencies.'),
 ('Pools and data','Eligible AHV placement, AOS/controller sharing, storage classes, image baseline, encryption/protection and failure headroom.'),
 ('Tenancy and policy','Project/RBAC entitlement distinct from VPC routing; provider-owned security categories/selectors and mandatory effective policy.'),
 ('Domain/edge attachment','Native VPC/subnet/gateway objects and supported external handoff. No-NAT is conditional; shared connected subnet isolation must be proven.'),
 ('Provisioning sequence','Installer-owned P2 foundation → address/attachment reservation → denied domain networks → edge/routes/policy → VM/disks → services and tests.'),
 ('Acceptance / failure','Same-host/cross-host controls, native routing, return symmetry, lost task response, protected data, HA placement and isolated restore.')],[1.71,5.43])
 b.p('The official provider repository publishes compatibility and resource-specific lifecycle notes. Use the exact supported combination and inspect replacement/update behaviour; a v2 resource name does not prove every needed operation. No provider release is selected by this kit. [K05]')
 b.external(['K05']);b.note('Stop when the actual gateway/handoff mechanism, required policy authority or resource lifecycle is unsupported or unproven. Use a reviewed alternative or exclude the capability; do not weaken the boundary to complete the run.')
 b.page(3,heads[2][1], 'Reference mapping: protected vCenter/ESXi and NSX management, eligible compute/storage pools, independent domain routing and an explicitly isolated upstream path to the required ZIP.', [('RA',17),('VND',4),('WD',8)])
 b.table(['Build concern','Specific engineering decision / receipt'],[
 ('Installation and transport','Actual vCenter/ESXi/NSX versions and hardware compatibility; transport nodes/zones, Edge placement, TEP/uplink reachability and management.'),
 ('Routing topology','Map Tier-1, distributed/service routing, Tier-0/VRF or approved alternative, advertisements, native routes and exact boundary next hops.'),
 ('Stateful enforcement and HA','Locate mandatory DFW and boundary functions; choose supported HA mode, state synchronization, return symmetry and failure load.'),
 ('Pools and data','Actual host eligibility/affinity, supported vMotion/restart, datastore/storage policy, images/virtual security devices and backup/key dependencies.'),
 ('Provisioning sequence','P2 compute/storage/NSX transport → scope and isolated upstream capacity → denied segments/gateways → policy → VM/data → service and path checks.'),
 ('Acceptance / failure','No unauthorized native/inter-VRF route; same-host rules, Edge/uplink loss, maintenance placement, support limits and useful restore.')],[1.71,5.43])
 b.p('Technical review item KIT-TN-01: Broadcom KB 442835 describes Tier-0 VRF incompatibility with an active-active stateful parent Tier-0. Reconcile this limitation with the selected release and architecture before choosing HA mode; do not assume every VRF/stateful combination is supported. [K09]')
 b.external(['K09']);b.note('The frozen RA remains unchanged. This kit adds a support check, not a command to change a live gateway. An HA-mode change needs separate disruption, session and recovery analysis.')
 b.page(4,heads[3][1], 'Reference mapping: selected OpenStack distribution; protected Keystone/control services; Nova/Placement compute; Neutron with a named backend; Glance/Cinder and separately selected data/protection services.', [('RA',18),('VND',5),('WD',8)])
 b.table(['Build concern','Specific engineering decision / receipt'],[
 ('Distribution and control','Service/database/messaging versions, certificates, API policy, installer/upgrade owner and controller recovery.'),
 ('Compute and data','Eligible host aggregates/traits/flavours with actual enforcement; images, boot/drivers, Cinder types/backends, storage credentials and protection.'),
 ('Network backend','Selected ML2/OVN or qualified alternative; controller/gateway/compute roles, mappings, distributed routes and external/provider attachments.'),
 ('Mandatory authority','Provider owns baseline security groups, port security, permitted address pairs and external mutation. Direct tenant editing is a qualified extension.'),
 ('Provisioning sequence','Supported distribution build → scoped project/quotas → denied networks/ports/routers and edge → instances/volumes → services and tests.'),
 ('Acceptance / failure','Effective additive policy, extra NIC/provider routes, metadata/DHCP, gateway/control loss, relocation, storage isolation and stale port/router cleanup.')],[1.71,5.43])
 b.p('Neutron describes security groups as additive allow controls; do not treat several groups as a provider deny hierarchy. OVN distributed routing must be included in path analysis, and Nova placement controls must be configured rather than inferred from an aggregate name. [K06–K08]')
 b.external(['K06','K07','K08']);b.note('Do not compete with Neutron by directly managing the same backend OVN objects. If the selected API/policy combination cannot protect the required baseline, the corresponding delegated capability is not offered.')
 b.page(5,heads[4][1], 'Reference mapping: provider-owned routed transport, qualified host/appliance attachment, optional EVPN/VXLAN where needed, and separately protected hardware recovery and management.', [('RA',5),('RA',6),('NET',1),('NET',5)])
 b.table(['Build concern','Specific engineering decision / receipt'],[
 ('Inventory and ports','Actual switch/network OS/NIC/optic/firmware compatibility, port map, power/failure grouping and staging identity.'),
 ('Underlay','Link/loopback allocations, permitted peers/ASNs, explicit import/export, ECMP, control-plane protection and maximum-prefix handling.'),
 ('Optional fabric overlay','RD/RT/VNI authority, gateway location, supported route types, BUM/ARP/ND and explicit route-import restrictions.'),
 ('Multihoming','Chosen MLAG or EVPN mechanism, peer/ES dependencies, orphan and split-brain behaviour; no assumed cross-vendor MLAG pair.'),
 ('Platform/edge transport','Owned tunnel endpoint networks, dedicated/qualified handoffs, actual encapsulation and minimum surviving MTU.'),
 ('Commission and recover','Supported network configuration owner, safe staged change, snapshots, constrained management, fault/recovery observations and accepted G1 receipt.')],[1.71,5.43])
 b.p('Use a site-specific network-OS annex after hardware selection. A Dell OS10 or other switch implementation must supply its actual provider or native configuration coverage and release-specific commands. The kit does not assert an unverified universal Terraform switch provider.')
 b.note('Physical placement and cabling execution use approved facility/manufacturer procedures and qualified personnel. Do not infer physical independence from two logical links terminating on the same failure dependency.')
 b.page(6,heads[5][1], 'These resources are required integrations, not incidental dependencies automatically supplied by the selected hypervisor provider.', [('RA',9),('SVC',1),('SVC',5),('WD',7)])
 b.table(['Service track','Native design and implementation receipt'],[
 ('Security edge','EC/SE or equivalent contexts, exactly scoped routes/interfaces/policy, joint boundary authority, required inspection, session behaviour, HA and management.'),
 ('IPAM/name/time','Delegated address authority, reservations/leases, DNS forward/reverse and approved resolvers including needed TCP/UDP, time profile and ownership.'),
 ('Identity and trust','Enterprise roles/federation, workload and runner identities, certificate lifecycle, key-use/admin/recovery scope and independent bootstrap.'),
 ('Storage/data','Owned virtual disks, file/object endpoint authorization, shared backend implications, capacity/QoS, snapshots/replication and sanitization.'),
 ('Backup/recovery','Capture orchestration versus transfer path, repository protection, catalogue/keys, retained-copy ownership and isolated useful restore.'),
 ('Telemetry and supply','Attributable event collection, buffering/loss handling, authorized search/retention, trusted images/artifacts and publication authority.')],[1.71,5.43])
 b.p('Each track publishes a handoff containing actual identity, permitted use, capacity/limits, support version, lifecycle owner, current acceptance restrictions and evidence. Sharing a reference does not require sharing the producer’s privileged credentials or full Terraform state.')
 b.p('SVC-REF is an illustrative shared-service domain, not permission for all provider traffic. Service-side return routing, source validation and backend entitlement remain part of qualification. Record each service’s compromise and outage dependency.')
 b.page(7,heads[6][1], 'Complete this review for each selected platform and all dependencies used by the offered service. A moving “latest” documentation page is context; retain the exact supported release evidence for the actual installation.', [('VND',7),('ET',8),('IK',4)])
 b.table(['Decision/check','Evidence and disposition'],[
 ('Native resource mapping','Reference IDs → actual platform objects, interfaces, hosts, data objects and owners.'),
 ('Compatibility and entitlements','Exact tuple plus official support matrix/release notes and actual enabled features.'),
 ('Operation coverage','Per-resource observe/create/update/adopt/replace/delete and interrupted-task discovery with a supported alternative where needed.'),
 ('Control/function coverage','Every required boundary, identity, data, placement and recovery function has an enforcement location and an observation.'),
 ('Limits and failures','Measured service capacity, relevant HA/partition behaviours and forbidden alternative paths.'),
 ('Variations and residual gaps','Changed design requires appropriate approval and new assertions; no automatic portability claim.'),
 ('Readiness','Qualification scoped by class/family; required operational recovery evidence before production; ongoing requalification triggers.')],[1.75,5.39])
 b.p('Use source IDs K05–K09 as current research entry points and the frozen RA/VND as architecture lineage. Source discovery does not approve a product combination. A feature gap should become a documented alternative, a limited service offer or a blocking issue.')
 b.note('These cards are implementation specifications and checklists. Actual modules, native installation/configuration artifacts, environment values and live evidence are separate required outputs—not represented as already delivered.')
 b.save()

if __name__=='__main__':build_ek();build_et();build_vc()
