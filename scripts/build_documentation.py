#!/usr/bin/env python3
"""Build Markdown navigation, decision records and traceability from reviewed local records.

This does not convert or overwrite chapter prose. Run convert_word_docs.py explicitly
only to review a source refresh. No network access or infrastructure changes occur.
"""
from __future__ import annotations
import csv
import hashlib
import html
import json
from pathlib import Path
import re
from urllib.parse import quote
from convert_word_docs import rel_link, slug
from adr_lifecycle import render as render_adr, validate as validate_adrs

ROOT=Path(__file__).resolve().parents[1]
BEGIN='<!-- BEGIN GENERATED DECISION LINKS -->'
END='<!-- END GENERATED DECISION LINKS -->'

class Builder:
    def __init__(self,root=ROOT):
        self.root=root
        self.sources=json.loads((root/'sources/documentation/conversion_manifest.json').read_text())['documents']
        self.byid={s['id']:s for s in self.sources}
        self.adrs=json.loads((root/'sources/documentation/adr_records.json').read_text())
        self.shared=root/'reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared'
        self.outputs=[]

    def write(self,path,text):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True)
        text=re.sub(r' {2,}\n','<br>\n',text)
        p.write_text(text.rstrip()+'\n',encoding='utf-8');self.outputs.append(path)

    def link(self,origin,target,label,anchor=''):
        return f'[{label}]({rel_link(self.root/origin,self.root/target,anchor)})'

    def section(self,ident,number=None):
        s=self.byid[ident]
        if number is None:return s['index']
        matching=[c for c in s['chapters'] if re.match(r'^'+str(number)+r'\.\s',c['title'])]
        if not matching and ident=='IMP04':matching=s['chapters'][number-1:number]
        if len(matching)!=1:raise ValueError(f'Unresolved source section {ident} {number}: {matching}')
        return matching[0]['path']

    def slink(self,origin,ident,number=None,label=None):
        return self.link(origin,self.section(ident,number),label or (ident+(f' §{number}' if number else ' — '+self.byid[ident]['title'])))

    def adrpath(self,a):return 'docs/adr/'+a['id'][4:]+'-'+slug(a['title'])+'.md'

    def read_csv(self,name):
        with (self.shared/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

    def source_sections(self,origin,text):
        return ' · '.join(self.slink(origin,m.group(1),int(m.group(2))) for m in re.finditer(r'([A-Z]+)\s*§\s*(\d+)',text)) or text

    def make_adrs(self):
        p='docs/adr/0002-markdown-first-source-backed-documentation.md'
        self.write(p,f'''# ADR-0002 — Markdown-first, source-backed architecture documentation

Status: Proposed publishing decision for this repository package. This implements the requested documentation layout, not an organizational security approval.

## Context

The earlier repository catalogue exposed binary files but not their full content to code review. Infrastructure decisions were embedded in chapters, tables and worked designs, while only one repository-organization ADR was visible.

## Decision

Keep chapter-sized Markdown in the role and subject directories under `docs/`. Preserve the original document bytes at their existing reference paths. Resolve converted Word cross-references to Markdown sections and retain actual diagram assets. Maintain the source hash, document/version, original section and conversion ledger so that a reader can distinguish a source transcription from new synthesis.

Extract documented architecture choices into proposed ADRs, preserving original decision identifiers. Do not invent an acceptance date, signatory, completed test, rejected-option meeting or missing source document. Keep historical audits and superseded handbook text in `docs/archive/` with an explicit historical banner.

## Relationship to ADR-0001

{self.link(p,'docs/adr/0001-architecture-first-repository.md','ADR-0001')} establishes the repository layout and preservation of original paths. This decision supplements its binary catalogue with full Markdown content; it does not replace its separation of architecture, engineering and implementation.

## Alternatives and consequences

A catalogue alone was insufficient for the requested Git documentation. One large Markdown file per original would preserve text but make review and linking cumbersome. Rewriting from general knowledge would obscure lineage and could change the supplied architecture. Chapter decomposition preserves the source organization while subject indexes connect related content.

Converted chapter paths are immutable source transcriptions. Maintained design records live under `docs/current/`, with explicit parent sections, versions and change history. Edit current records through review without preserving superseded source wording merely to pass the transcription gate. Frozen-source refresh is prohibited from targeting `docs/current/`. ADR records and their governance fields are authoritative for generated ADR pages; no approval is inferred from a merge.

## Scope and exclusions

This is not a new architecture approval, site design, live qualification, or assertion that historical contract defects were repaired. Workbooks and native infrastructure code are unchanged. Standalone RAD/TAD v1.2 source files were not present; the RAD and TAD pages in this package are clearly identified reading views over available material.

## Verification and maintenance

Use {self.link(p,'docs/DOCUMENTATION_MIGRATION.md','the migration procedure')} and `python scripts/check_documentation.py` to verify source hashes, block coverage, images, tables, fields, links, decision identifiers and source-derived ADR status. Review architecture status separately from passing documentation checks.
''')
        lifecycle_errors=validate_adrs(self.adrs)
        if lifecycle_errors:raise ValueError('; '.join(lifecycle_errors))
        cross=[]; backlinks={}
        for a in self.adrs:
            p=self.adrpath(a);refs=' · '.join(self.slink(p,s,n) for s,n in a['source_sections'])
            sourceids=', '.join('`'+x+'`' for x in a['source_decision_ids']) or 'No standalone source ID; extracted from the explicitly linked chapter decisions.'
            reqs=' · '.join(self.link(p,'docs/assurance/requirements.md',x,x) for x in a['requirements'])
            code='\n'.join('- '+self.link(p,x,x) for x in a['implementation_paths'])
            text=render_adr(a,self)
            self.write(p,text)
            for s,n in a['source_sections']:
                target=self.section(s,n);backlinks.setdefault(target,[]).append(a)
                cross.append({'adr':a['id'],'title':a['title'],'status':a['status'],'originalDecisionIds':'; '.join(a['source_decision_ids']), 'sourceId':s,'sourceSection':str(n),'markdownSource':target,'adrPath':p})
        for target,items in backlinks.items():
            p=self.root/target;txt=p.read_text()
            txt=re.sub(re.escape(BEGIN)+r'.*?'+re.escape(END),'',txt,flags=re.S).rstrip()
            block='\n\n'+BEGIN+'\n\n## Related decision records\n\n'+'\n'.join('- '+self.link(target,self.adrpath(a),a['id']+' — '+a['title']) for a in items)+'\n\n'+END+'\n'
            p.write_text(txt+block)
        path=self.root/'sources/documentation/adr_crosswalk.csv'
        with path.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(cross[0]));w.writeheader();w.writerows(cross)
        idx='docs/adr/README.md'
        lines=['# Architecture decision register','',
          'These are decisions from the architecture and engineering sources, not a generic list of software choices. Source-derived records use the lifecycle state shown below. The initial conversion remains Proposed; any later Accepted, Rejected or Superseded record requires actual decision metadata and independently reviewed evidence. Rendering does not authenticate that authority or issue native qualification.',
          '', 'The repository numbering and original source numbering are separate. AD-01–AD-15, RD14-01–RD14-05 and DEV-ADR-01 are mapped below; thematic decisions are linked to their source chapters without inventing a historical identifier.',
          '', '| Record | Source decision | Source / status |','| --- | --- | --- |',
          '| '+self.link(idx,'docs/adr/0001-architecture-first-repository.md','ADR-0001 — Repository structure')+' | Existing repository decision | Proposed; preserved |',
          '| '+self.link(idx,'docs/adr/0002-markdown-first-source-backed-documentation.md','ADR-0002 — Markdown-first migration')+' | New editorial decision | Proposed publishing convention |']
        for a in self.adrs:
            lines.append('| '+self.link(idx,self.adrpath(a),a['id']+' — '+a['title'])+' | '+(', '.join(a['source_decision_ids']) or 'Chapter-derived')+' | '+self.slink(idx,*a['source_sections'][0])+'; '+a['status']+' |')
        lines+=['','## Add or change a decision','',self.link(idx,'docs/adr/template.md','Use the source-grounded ADR template')+'. Keep decision ownership, source basis, alternatives, constraints, implementation effects and approval status distinct. Add evidence only when it actually exists. See the '+self.link(idx,'sources/documentation/adr_crosswalk.csv','machine-readable crosswalk')+'.']
        self.write(idx,'\n'.join(lines))
        self.write('docs/adr/template.md','''# ADR-NNNN — Decision title

Status: Proposed | Accepted | Superseded | Rejected (choose one)<br>
Date of actual decision: Not recorded; required for a non-Proposed transition<br>
Accountable role / authority: Assign the accountable role; do not invent an approving person<br>
Scope: Define applicability<br>
Decision record, rationale and evidence references: Required for non-Proposed states<br>
Superseded by: Required only for Superseded; must refer to an accepted successor without cycles<br>
Original source decision ID, version and chapter: To be linked

## Context

State the infrastructure problem and constraints supported by the linked source. Mark any new assumptions as proposed.

## Decision

State the selected scope, components, authority and lifecycle boundary. Do not imply a deployment occurred.

## Alternatives considered

Distinguish alternatives actually recorded in source documents from newly proposed alternatives. Record why the option was selected and the acceptance conditions on variations.

## Security, portability and operational consequences

Identify affected zones, management access, shared resources, failure domains, capacity, maintenance and exit constraints.

## Engineering and provisioning obligations

Link the technical design, interfaces, resource ownership, work package, native implementation and verification method.

## Requirement and evidence links

Link the exact requirement IDs, test assertions, code and actual evidence. Keep not-run tests as not-run.

## Acceptance and supersession

Record an actual accepting authority, scope, date and evidence only when supplied. Reference any superseded ADR; do not reuse an ID for a different decision.
''')
        existing=self.root/'docs/adr/0001-architecture-first-repository.md'
        s=existing.read_text()
        if 'Markdown-first follow-up' not in s:
            existing.write_text(s.rstrip()+'\n\n## Markdown-first follow-up\n\n[ADR-0002](0002-markdown-first-source-backed-documentation.md) adds full chapter content and source-derived decision records while preserving these original paths.\n')

    def catalogues(self):
        reqs=self.read_csv('requirements.csv');p='docs/assurance/requirements.md'
        lines=['# Requirement catalogue — retained wording','',
          'The 194 statements below are transcribed from the retained delivery-kit requirement CSV. Source editions, applicability and execution status are not re-approved here. Requirement-to-code links are traceability, not a claim that every control is implemented.',
          '', self.link(p,'reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/requirements.csv','Original requirement register')+' · '+self.link(p,'docs/assurance/test-specifications.md','Test specification register'), '']
        for r in reqs:
            ident=r['requirementId'];lines += [f'<a id="{ident}"></a>',f'## {ident}', '', r['text'], '',
             '| Source field | Retained value |','| --- | --- |',
             '| Accountable role | '+r['ownerRole']+' |',
             '| Parent sections | '+self.source_sections(p,r['parentSections'])+' |',
             '| Supplement homes | '+self.source_sections(p,r['supplementHomes'])+' |',
             '| Source IDs | '+r['sourceIds']+' |',
             '| Wording disposition | '+r['wordingDisposition']+' |',
             '| Execution status | '+r['executionStatus']+' |',
             '| Tests | '+' · '.join(self.link(p,'docs/assurance/test-specifications.md',t,t) for t in r['baselineTests'].split('; '))+' |','']
            matches=[a for a in self.adrs if ident in a['requirements']]
            if matches:lines+=['Related ADRs: '+' · '.join(self.link(p,self.adrpath(a),a['id']) for a in matches),'']
        self.write(p,'\n'.join(lines))
        p='docs/assurance/test-specifications.md';lines=['# Inherited test specifications','',
          '**All 80 results below retain their source execution status.** This documentation migration does not run infrastructure tests. Later packet/HTTPS fixture evidence is separately scoped and cannot silently satisfy the complete native procedure.', '',self.link(p,'reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/tests.csv','Original test register'),'']
        for r in self.read_csv('tests.csv'):
            lines += [f'<a id="{r["id"]}"></a>',f'## {r["id"]} — {r["title"]}','']
            for k in ('preconditions','procedure','expected','evidence','mode','cadence','executionStatus'):
                lines += ['**'+k+':** '+r[k],'']
            lines+=['Requirement links: '+' · '.join(self.link(p,'docs/assurance/requirements.md',x,x) for x in r['requirements'].split('; ')),'']
        self.write(p,'\n'.join(lines))
        # Complete navigation to original data; no copied status pretending to be live.
        p='docs/assurance/registers.md';lines=['# Design, gap and execution registers','',
          'The original records remain editable source artifacts with their original status. The following index is navigation, not a duplicate project database.','', '| Register | Purpose |','| --- | --- |']
        records=[('reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/requirements.csv','194 requirement statements'),
                 ('reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/tests.csv','80 inherited test specifications'),
                 ('reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/site_decisions.csv','Twelve unresolved site decisions'),
                 ('reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/open_v14_decisions.csv','Open connected-design implementation decisions'),
                 ('reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/gates.csv','Gate responsibilities and prerequisites'),
                 ('reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/registers/v1_4_gate_dependencies.csv','Initial readiness and activation dependencies'),
                 ('sources/implementation_backlog.csv','Increment 04 native integration backlog'),
                 ('sources/documentation/section_map.csv','Word section to Markdown chapter map'),
                 ('sources/documentation/adr_crosswalk.csv','Source decision to ADR map')]
        for f,label in records:
            lines.append('| '+self.link(p,f,Path(f).name)+' | '+label+' |')
        self.write(p,'\n'.join(lines))

    def category(self,path,title,intro,ids,extra=(),tail=''):
        rows=['# '+title,'',intro,'','| Content | How to use it |','| --- | --- |']
        for ident,purpose in ids:
            rows.append('| '+self.slink(path,ident)+' | '+purpose+' |')
        rows+=['','These links open the full converted narrative, tables, placeholders, diagrams and cross-references—not a summary of the Word files. Source metadata and originals remain linked in every chapter.']
        for target,label in extra:rows+=['',self.link(path,target,label)]
        rows+=['',self.link(path,'docs/README.md','Documentation home')+' · '+self.link(path,'docs/adr/README.md','Architecture decisions')]
        if tail: rows+=['',tail.strip()]
        self.write(path,'\n'.join(rows))

    def navigation(self):
        self.category('docs/architecture/README.md','Architecture',
          'Begin with the v1.4 infrastructure reference. The RAD view supplies a reading path through the reusable scope, trust boundaries and adoption decisions; it is not a fabricated copy of an unavailable standalone RAD.',
          [('RA','Primary source architecture and its 30 chapters / appendices'),('AK','Architecture delivery and engineering handoff'),('SVC','Provider shared services, data boundaries, identity and recovery')],
          [('docs/architecture/RAD.md','RAD — Reference architecture reading view'),('docs/solutions/README.md','Solution design and worked environments')])
        self.category('docs/engineering/README.md','Engineering',
          'The engineering view translates the architecture into connected infrastructure responsibilities and supported native realizations. Actual site values and approvals remain unresolved where the sources leave them unresolved.',
          [('EK','Engineering method and handoff'),('NET','Fabric, routing, multihoming, MTU and management'),('NBD','Detailed forward/reply paths and interface acceptance'),('VND','Common fixture across the three stacks'),('PBS','Platform commissioning and tenant build responsibilities'),('VRC','Vendor and shared-infrastructure build cards')],
          [('docs/engineering/TAD.md','TAD — Technical architecture reading view'),('docs/engineering/platform-capability-registry.md','Machine-readable platform capability registry and evidence boundary'),('docs/templates/lld/README.md','Editable low-level design template')],tail='## Implemented laboratory work packages\n\n[Routed IPv6 path, protocol, MTU and service engineering](routed-ipv6-qualification.md) develops the declared family requirements into an executable fixed local experiment, while retaining the native-site acceptance obligations.\n\n[Bounded Nutanix task-tree readback](nutanix-task-tree-readback.md) connects native task identities, complete child/entity coverage and selected VPC/subnet observations to the existing controlled recovery handoff. It is not full native qualification or a new deployment authority.')
        self.category('docs/solutions/README.md','Solution designs and worked delivery',
          'Use these full source chapters to develop the service-specific solution. The internal OZ/RZ environment is a proposed reference fixture, not an accepted production site. No missing public-service solution document is invented.',
          [('SDP','Service scope, alternatives and decision development'),('WD','Connected component, address, route, service, build and acceptance schedules'),('WDE','A worked path from design through delivery evidence')],
          [('docs/templates/hld/README.md','High-level / solution design working template')])
        self.category('docs/implementation/README.md','Implementation and commissioning',
          'Infrastructure work packages and ownership lead. Tool descriptions remain subordinate to the architecture and distinguish source code, local fixtures, native qualification and activation authority.',
          [('PROV','P0–P6 scopes, commissioning, changes and safe retirement'),('IK','Implementation release and handover method'),('IMP04','Actual Increment 04 readback and recovery scope')],
          [('docs/implementation/code-map.md','Architecture / decision / implementation map'),('docs/templates/implementation-mop/README.md','Method-of-procedure and handover templates'),('docs/COMMISSIONING.md','Existing executable commissioning procedure')],tail='## Executable verification extensions\n\n[I08 routed IPv6 packet, shared-service and recovery experiment](routed-ipv6-lab.md) · [Engineering choices and native qualification boundary](../engineering/routed-ipv6-qualification.md). This adds a local packet layer to the existing model and endpoint tests without changing native provisioning resources.\n\n[I09 known Nutanix task-tree readback](nutanix-task-tree-readback.md) adds an optional bounded parent/child profile and linked local HTTPS/recovery campaign. The existing single-task profile remains unchanged.\n\n## Native reference-service commissioning\n\n[Native reference-service commissioning kit](native-reference/README.md) connects actual site inputs, provider-specific build responsibilities, foundation-service interfaces, W14 observation planning, recovery and retirement. It is an unexecuted planning kit; exported worksheets do not grant deployment or operating authority.')
        self.category('docs/operations/README.md','Operations, recovery and transition',
          'The source playbook links actual infrastructure dependency loss, interrupted change, recovery order, migration, retention and operating responsibility.',
          [('OPS','Full operational playbook'),('SVC','Shared-service failure and recovery architecture')],
          [(self.section('RA',27),'Parent architecture: recovery, migration and retirement')])
        self.category('docs/assurance/README.md','Assurance, audit and acceptance',
          'Maintain separate status for documentation treatment, code coverage, local observation, native qualification and formal operating authorization. Historical audit findings remain historical; reformatting them does not close them.',
          [('GM','Gap map and unresolved decision package'),('QUAL','Site-specific qualification, controls and handover'),('QCP','Campaign selection, observations, evidence and disposition')],
          [('docs/assurance/requirements.md','Complete requirement catalogue'),('docs/assurance/test-specifications.md','Complete inherited test specifications'),('docs/assurance/implementation-audit.md','Implementation coverage and audit boundaries'),('docs/assurance/registers.md','Original editable registers'),('docs/archive/README.md','Historical audits and source lineage')])
        self.category('docs/templates/README.md','Working design and acceptance templates',
          'Original editable-field prompts are retained as Markdown values. Copy a template into a controlled solution/site working area; do not mark sample placeholders as accepted data.',
          [('AT','HLD and architecture review'),('ET','LLD and engineering review'),('IT','Implementation method, qualification and handover')])
        self.category('docs/governance/README.md','Delivery governance',
          'Gates identify decisions and evidence dependencies, not a sequence implied by their numbers.',
          [('DEL','Current delivery map and ownership')],
          [('docs/adr/README.md','Decision register'),('docs/DOCUMENTATION_MIGRATION.md','Documentation maintenance and provenance')])
        self.category('docs/archive/README.md','Historical source and audit archive',
          '**Historical only.** These documents retain their original wording and historical claims. They are not the current architecture or proof that the old software-contract package was repaired. The v1.2 content review describes a separate editorial branch; it has not been silently merged into the active v1.4 source.',
          [('HB10','Original 43-page architecture lineage, including original ADR template'),('HB11','Expanded handbook and original contract-heavy appendices'),('AUD11','Full independent v1.1 audit findings and closure criteria'),('REV12','Full content-disposition review'),('DEL10','Earlier delivery-map edition')])
        for path,title,rows in [
          ('docs/architecture/RAD.md','RAD — Reference architecture reading view',[
            ('Scope, drivers and proposed authority',[('RA',1),('RA',2)]),
            ('Physical context and commissioned capacity',[('RA',3),('RA',4),('RA',5)]),
            ('Management, tenancy and security boundaries',[('RA',6),('RA',7),('RA',8)]),
            ('Shared services, data, identity and continuity',[('RA',9),('RA',12),('RA',13),('RA',14)]),
            ('Portability, realization and provisioning strategy',[('RA',15),('RA',20),('RA',24)]),
            ('Decisions, adoption and acceptance',[('RA',28),('RA',29),('RA',30),('SDP',3)])]),
          ('docs/engineering/TAD.md','TAD — Technical architecture reading view',[
            ('Translate the accepted architecture into engineering',[('EK',1),('PBS',1)]),
            ('Transport, interfaces and return routing',[('NET',1),('NET',2),('NBD',2),('NBD',3),('NBD',6)]),
            ('Nutanix hosting cell and tenant build',[('VND',3),('PBS',2),('PBS',3)]),
            ('VMware/NSX routing, transport and policy',[('VND',4),('PBS',4),('PBS',5)]),
            ('OpenStack backend and mandatory authority',[('VND',5),('PBS',6),('PBS',7)]),
            ('Connected resources, service paths and tooling ownership',[('WD',3),('WD',4),('WD',6),('WD',7),('PROV',3)]),
            ('Capacity, failure, build release and acceptance',[('WD',9),('WD',11),('WD',12),('PBS',9),('QUAL',5)])])]:
            text=['# '+title,'','This is a new **composition / navigation view of available source content**, not a recovered standalone RAD or TAD file. The original standalone v1.2 package was not available in the supplied commit-ready ZIP. All substantive chapters below are full source transcriptions, with source/version and original file links.', '', '| Design concern | Full source chapters |','| --- | --- |']
            for topic,refs in rows:text.append('| '+topic+' | '+' · '.join(self.slink(path,*x) for x in refs)+' |')
            text += ['',self.link(path,'docs/adr/README.md','Decision register')+' · '+self.link(path,'docs/solutions/README.md','Solution design')+' · '+self.link(path,'docs/templates/README.md','Working templates')]
            self.write(path,'\n'.join(text))
        p='docs/README.md'
        self.write(p,f'''# Portable multi-tenant secure hosting — documentation

**Infrastructure architecture → engineering → solution design → implementation → operational acceptance.**

This repository now contains the Word documents' actual content as Markdown chapters. The active source baseline remains the supplied v1.4 reference architecture, delivery-kit v1.1 development documents and Implementation Increment 04. Conversion does not issue approval or replace unknown site values with defaults.

| Start with | Content |
| --- | --- |
| [Architecture](architecture/README.md) / [RAD reading view](architecture/RAD.md) | Scope, physical/logical design, security and service boundaries, portability and adoption |
| [Engineering](engineering/README.md) / [TAD reading view](engineering/TAD.md) | Fabric, native stacks, forward/reply paths, dependencies and supported build responsibilities |
| [Solution designs](solutions/README.md) | Service alternatives and a connected two-tenant OZ/RZ worked environment |
| [Implementation](implementation/README.md) | Commissioning work packages, code coverage, readback, safe stopping and handover |
| [Operations](operations/README.md) | Change, recovery, migration, failback, retention and operating ownership |
| [Assurance](assurance/README.md) | Gap map, requirements, test specifications, qualification and audit boundaries |
| [ADRs](adr/README.md) | Proposed source-backed design decisions and original decision-ID mapping |
| [Templates](templates/README.md) | Full HLD, LLD, implementation, review and acceptance prompts |
| [Governance](governance/README.md) | Delivery framework, gate dependencies and responsibilities |
| [Archive](archive/README.md) | Historical handbook editions, audit and content-disposition review |

## Review one connected path

Read {self.slink(p,'RA',8,'the inter-domain boundary')} → {self.slink(p,'NBD',2,'its forward and return routing')} → {self.slink(p,'WD',8,'its vendor realization')} → {self.slink(p,'PROV',4,'its provisioning sequence')} → {self.slink(p,'QCP',3,'its verification observations')}. The chapters preserve their source diagrams, tables and cross-references.

## Source and change rules

[Conversion coverage and maintenance](DOCUMENTATION_MIGRATION.md) records what was moved, what is historical and what source artifacts were unavailable. [The binary catalogue](ARTIFACT_CATALOG.md) remains for provenance and workbook access. The [implementation coverage map](implementation/code-map.md) distinguishes candidate code from actual platform qualification.

Do not silently change inherited requirements while copying them into an ADR. Source-derived ADRs have no recorded organizational acceptance. Initial operational and promised recovery readiness remains a prerequisite to production activation—not a later paperwork step.
''')

    def code_map(self):
        p='docs/implementation/code-map.md'
        rows=[
          ('Nutanix domains and staged workloads',[('RA',16),('PBS',2),('PBS',3)],['ADR-0024','ADR-0008'],['terraform/modules/nutanix-domain','terraform/roots/nutanix-domain','terraform/modules/nutanix-workload','terraform/roots/nutanix-workload'],'Candidate native resources; actual Flow, placement, storage and external handoff behaviour requires target qualification.'),
          ('VMware/NSX domain, workload, route and quarantine',[('RA',17),('PBS',4),('PBS',5)],['ADR-0025','ADR-0015'],['terraform/modules/nsx-domain','terraform/modules/vsphere-workload','terraform/modules/nsx-route','terraform/modules/nsx-gateway-quarantine'],'These resource scopes do not supply a complete Tier-0/VRF/Edge construction or qualified end-to-end ZIP.'),
          ('OpenStack domain, workload and route',[('RA',18),('PBS',6),('PBS',7)],['ADR-0026','ADR-0023'],['terraform/modules/openstack-domain','terraform/modules/openstack-workload','terraform/modules/openstack-route'],'Backend, port-security authority, scheduler, boot behaviour, storage and effective paths remain native qualification work.'),
          ('Exact route engineering and review',[('RA',10),('NBD',2),('WD',6)],['ADR-0007','ADR-0035'],['tools/route_audit.py','tools/route_record_review.py','tools/plan_review.py','terraform/modules/nutanix-route'],'Offline graphs and exact-record checks are not observations of a live routing table or approval provenance.'),
          ('DNS service-owner lifecycle',[('SVC',2),('RA',10)],['ADR-0020','ADR-0010'],['tools/dns_change.py','docs/DNS_LIFECYCLE.md','lab/run_dns_lab.py'],'The candidate RFC2136 client and local fixture do not allocate IPAM addresses, qualify a DNS product or prove cache propagation.'),
          ('Native readback and interrupted change',[('PROV',5),('OPS',3)],['ADR-0031','ADR-0032'],['tools/nsx_observe.py','tools/nutanix_observe.py','tools/neutron_observe.py','tools/recovery_review.py'],'Selected reads and offline recovery checks do not perform true writer fencing, platform repair or authorization.'),
          ('Service identity and packet fixture',[('RA',13),('QCP',4)],['ADR-0029','ADR-0017'],['lab/run_namespace_lab.py','lab/mtls_fixture.py'],'Local IPv4 mutual-TLS and resource-grant observations do not qualify enterprise PKI, KMS, backup, native IPv6 or vendor HA.'),
          ('Local Ansible staging and expectation validation',[('PROV',1),('PROV',3)],['ADR-0013','ADR-0016'],['ansible/roles','ansible/playbooks','scripts/verify_ansible.py'],'New candidate localhost-only roles; not native switch, hypervisor or firewall configuration.'),
          ('Source checks and engine gates',[('QUAL',5),('QCP',6)],['ADR-0017'],['tools/check_local.py','scripts/check_repository.py','tools/verify_terraform.py','.github/workflows/validate.yml'],'Current documentation checks are separate from native engine/CI or platform runs. Historical results retain their exact scope.')]
        text=['# Architecture, decisions and implementation coverage','',
              'This map connects existing source code to the supplied design. It is a documentation integration, not new native functionality or a fresh deployment audit. Read the actual module/tool limitations and collect target-specific evidence before claiming conformance.','']
        byadr={a['id']:a for a in self.adrs}
        for title,refs,adrs,paths,limit in rows:
            text+=['## '+title,'','Design: '+' · '.join(self.slink(p,*x) for x in refs),'',
              'Decisions: '+' · '.join(self.link(p,self.adrpath(byadr[x]),x) for x in adrs),'',
              'Implementation: '+' · '.join(self.link(p,x,x) for x in paths),'',limit,'']
            for x in paths:
                if not (self.root/x).exists():raise ValueError('Missing code mapping '+x)
        text+=['## Platform capability registry','',
          'Design: '+self.link(p,'docs/architecture/reference/15-cross-vendor-realization-model.md','Cross-vendor realization model')+' · '+self.link(p,'docs/assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md','Site qualification and evidence'),'',
          'Implementation: '+self.link(p,'sources/capabilities/platform_registry.json','machine-readable registry')+' · '+self.link(p,'scripts/check_platform_capabilities.py','registry checker')+' · '+self.link(p,'docs/engineering/platform-capability-registry.md','engineering evidence boundary'),'',
          'The registry distinguishes candidate source and local fixtures from native qualification. It currently makes no platform production-eligible and does not perform placement.','',
          '## Open native work','',self.link(p,'sources/implementation_backlog.csv','The inherited implementation backlog')+' remains the source record for installed target selection, effective security edges, authoritative service integration, native IPv6, actual fencing and production readiness. This conversion does not close those items.']
        self.write(p,'\n'.join(text))
        p='docs/assurance/implementation-audit.md'
        self.write(p,f'''# Implementation and audit reading map

## Basis and boundary

This is a source-backed integration map, not a new deployed-system security assessment. The full {self.slink(p,'AUD11',None,'v1.1 independent audit')} and {self.slink(p,'REV12',None,'architecture-led content review')} are preserved in the historical archive. Their original findings, proposed corrections and scope limitations remain intact. The legacy API/schema defects are not labelled repaired by removing them from the main infrastructure narrative.

## Distinguish the evidence layers

| Layer | Read | What it does not establish |
| --- | --- | --- |
| Architecture decision | {self.slink(p,'RA',29)} and {self.link(p,'docs/adr/README.md','ADRs')} | A proposed pattern is not an accepted site design |
| Engineering completeness | {self.slink(p,'NBD',6)} and {self.slink(p,'PBS',9)} | A populated record is not a supported or deployed configuration |
| Code coverage | {self.link(p,'docs/implementation/code-map.md','Code map')} | A module or reader name is not full lifecycle or security coverage |
| Local fixture observations | {self.link(p,'quality/README.md','Historical report context') if (self.root/'quality/README.md').exists() else self.link(p,'quality/local_validation.json','Preserved increment report')} | A local model, protocol server or namespace is not vendor qualification |
| Native campaign | {self.slink(p,'QUAL',5)} and {self.slink(p,'QCP',6)} | No native execution is asserted by conversion |
| Operational authorization | {self.slink(p,'RA',28)} and {self.slink(p,'QUAL',7)} | A successful command or document check cannot issue authorization |

## Current documentation treatment

The conversion supplies complete chapter text, tables, diagrams and working prompts; an explicit Word-section-to-Markdown map; bidirectional links to decisions; and requirement, implementation and verification navigation. The migration report checks these publishing properties only.

## Outstanding implementation decisions

Retain the source gaps in {self.slink(p,'GM',3)} and the {self.link(p,'sources/implementation_backlog.csv','native implementation backlog')}. Choose actual site/component versions, isolation and handoff construction, platform/API authority, real capacity and service limits, independent recovery dependencies and the evidence required by the offered service. No missing values or signatures are completed on behalf of an authority.

The numbers G0–G4 identify types of acceptance. As {self.slink(p,'WD',9)} states, the required initial operational and recovery readiness precedes production activation; continuing exercises do not substitute for that initial gate.
''')

    def section_map(self):
        rows=[]
        for s in self.sources:
            for c in s['chapters']:
                rows.append({'sourceId':s['id'],'sourcePath':s['source'],'sourceVersion':s['version'],'historical':s['historical'],
                 'sourceSection':c['title'],'sourceBlock':c['source_block'],'markdownPath':c['path'],'sourceSha256':s['source_sha256']})
        with (self.root/'sources/documentation/section_map.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

    def run(self):
        self.section_map();self.make_adrs();self.catalogues();self.navigation();self.code_map()
        for path in ['docs/README.md','docs/architecture/RAD.md','docs/engineering/TAD.md']:
            p=self.root/path
            p.write_text(p.read_text().rstrip()+'\n\n'+self.link(path,'docs/current/README.md','Maintained design workspace')+' — current editable records, separately versioned from frozen transcriptions. See '+self.link(path,'docs/assurance/completion-corrections.md','completion-audit dispositions')+'.\n')
        p=self.root/'docs/assurance/README.md'
        p.write_text(p.read_text().rstrip()+'\n\n[All verification families](verification-families.md) · [Historical finding dispositions](historical-dispositions.md) · [Assertion allocation](../implementation/assertion-allocation.md)\n')
        (self.root/'sources/documentation/integration_outputs.json').write_text(json.dumps(self.outputs,indent=2)+'\n')
        print(f'Built {len(self.outputs)} decision/catalogue/navigation pages; linked {len(self.adrs)} source-derived ADRs.')

if __name__=='__main__':Builder().run()
