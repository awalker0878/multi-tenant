#!/usr/bin/env python3
"""Check local release links, source lineage and documentation-result consistency.

Does not validate Terraform semantics, recalculate spreadsheets or contact providers.
Historical reference documents are checked for byte preservation, not requalified.
"""
from __future__ import annotations
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == 'href' and value: self.links.append(value)


def main() -> int:
    issues = []; checked_links = 0; checked_reference_files = 0
    def local_link(source: Path, target: str):
        nonlocal checked_links
        parsed = urlsplit(target)
        if parsed.scheme or not parsed.path: return
        checked_links += 1
        destination = (source.parent / unquote(parsed.path)).resolve()
        if not destination.is_relative_to(ROOT) or not destination.exists():
            issues.append({'kind':'BROKEN_LOCAL_LINK','file':str(source.relative_to(ROOT)),'target':target})

    for source in sorted(ROOT.rglob('*')):
        if not source.is_file() or 'reference' in source.relative_to(ROOT).parts: continue
        if source.suffix == '.md':
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', source.read_text()): local_link(source,target)
        elif source.suffix == '.html':
            parser = LinkParser(); parser.feed(source.read_text())
            for target in parser.links: local_link(source,target)
    guide = ROOT/'Implementation_Execution_Guide.docx'
    w = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    if not guide.exists():
        issues.append({'kind':'MISSING_EXECUTION_GUIDE'})
        bookmarks = []; table_count = 0
    else:
        with zipfile.ZipFile(guide) as archive:
            document = ET.fromstring(archive.read('word/document.xml'))
            bookmarks = [element.get(w+'name') for element in document.iter(w+'bookmarkStart')]
            if len(set(bookmarks)) != len(bookmarks): issues.append({'kind':'DUPLICATE_BOOKMARK'})
            for element in document.iter(w+'hyperlink'):
                anchor = element.get(w+'anchor')
                if anchor and anchor not in bookmarks: issues.append({'kind':'BROKEN_BOOKMARK','target':anchor})
            relationships = ET.fromstring(archive.read('word/_rels/document.xml.rels'))
            for element in relationships:
                if element.get('Type','').endswith('/hyperlink'): local_link(guide,element.get('Target',''))
            table_count=0
            for table in document.iter(w+'tbl'):
                table_count+=1
                first=table.find(w+'tr')
                if first is None or first.find(w+'trPr/'+w+'tblHeader') is None:
                    issues.append({'kind':'TABLE_HEADER_NOT_MARKED'})
            text=' '.join(element.text or '' for element in document.iter(w+'t'))
            local=json.loads((ROOT/'quality/local_validation.json').read_text())
            if f"{local['unit_and_source_tests']['run']} run; zero" not in text:
                issues.append({'kind':'GUIDE_TEST_COUNT_MISMATCH'})
    manifest=json.loads((ROOT/'sources/reference_checksums.json').read_text())
    for relative,expected in manifest.items():
        checked_reference_files+=1
        path=ROOT/relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            issues.append({'kind':'REFERENCE_BYTES_CHANGED','file':relative})
    inventory=json.loads((ROOT/'sources/module_inventory.json').read_text())
    for name, item in inventory.items():
        path=ROOT/'terraform/modules'/name/'main.tf.json'
        body=json.loads(path.read_text())
        if body['variable']!=item['variables']:
            issues.append({'kind':'MODULE_INPUT_INVENTORY_MISMATCH','module':name})
    roots = sorted((ROOT/'terraform/roots').glob('*/main.tf.json'))
    if len(inventory) != 10 or len(roots) != 10:
        issues.append({'kind':'RETAINED_NATIVE_INVENTORY_INCOMPLETE'})
    packet = json.loads((ROOT/'quality/local_packet_lab.json').read_text())
    if packet.get('status') != 'PASSED_NAMESPACE_FIXTURE' or packet.get('failed') != 0:
        issues.append({'kind':'RECORDED_PACKET_FIXTURE_NOT_PASSED'})
    if packet.get('original_namespace_configuration_unchanged') is not True:
        issues.append({'kind':'ORIGINAL_NAMESPACE_PRESERVATION_NOT_CONFIRMED'})
    fixture = ROOT/'examples/wd14-routing.json'
    if packet.get('fixture_sha256') != hashlib.sha256(fixture.read_bytes()).hexdigest():
        issues.append({'kind':'RECORDED_PACKET_FIXTURE_DIGEST_MISMATCH'})
    dns_report=json.loads((ROOT/'quality/local_dns_transactions.json').read_text())
    if dns_report.get('status') != 'PASSED_LOCAL_WIRE_FIXTURE' or dns_report.get('failed') != 0:
        issues.append({'kind':'DNS_WIRE_CAMPAIGN_NOT_PASSED'})
    native_report=json.loads((ROOT/'quality/local_native_readback.json').read_text())
    if native_report.get('status') != 'PASSED_LOCAL_HTTPS_FIXTURE' or native_report.get('failed') != 0:
        issues.append({'kind':'NATIVE_READBACK_FIXTURE_NOT_PASSED'})
    for report in (packet,dns_report,native_report):
        for relative,expected in report.get('source_sha256',{}).items():
            if not (ROOT/relative).is_file() or hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=expected:
                issues.append({'kind':'PROTOCOL_SOURCE_CHANGED_SINCE_EXECUTION','file':relative})
    snapshot=json.loads((ROOT/'quality/tested_source_manifest.json').read_text())
    for relative,expected in snapshot.items():
        if not (ROOT/relative).is_file() or hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=expected:
            issues.append({'kind':'SOURCE_CHANGED_SINCE_REGRESSION','file':relative})
    prior=json.loads((ROOT/'sources/increment02_manifest.json').read_text())['files']
    retained_native=0
    for relative,expected in prior.items():
        if relative.startswith('terraform/'):
            retained_native+=1
            if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=expected:
                issues.append({'kind':'RETAINED_NATIVE_SOURCE_CHANGED','file':relative})
    visual = json.loads((ROOT/'quality/visual_review.json').read_text())
    if visual.get('document_sha256') != hashlib.sha256(guide.read_bytes()).hexdigest():
        issues.append({'kind':'GUIDE_CHANGED_AFTER_VISUAL_REVIEW'})
    try:
        from tools.verify_terraform import plan_only_mock_tests
    except ModuleNotFoundError:
        from verify_terraform import plan_only_mock_tests
    for module in inventory:
        if not plan_only_mock_tests(ROOT/'terraform/modules'/module):
            issues.append({'kind':'MOCK_TEST_SOURCE_NOT_PLAN_ONLY','module':module})
    for path in (ROOT/'terraform').rglob('*'):
        if path.is_file() and ('.terraform' in path.parts or '.tfstate' in path.name or path.suffix=='.tfplan'):
            issues.append({'kind':'RUNTIME_ARTIFACT_IN_SOURCE','file':str(path.relative_to(ROOT))})
    status='PASSED_PACKAGE_CHECKS_ONLY' if not issues else 'FAILED_PACKAGE_CHECKS'
    report={
        'status':status,'checked_new_document_links':checked_links,
        'guide_bookmarks':len(bookmarks),'guide_tables':table_count,
        'frozen_reference_files_checked':checked_reference_files,
        'module_inventory_records_checked':len(inventory),
        'root_configs_checked':len(roots),'plan_only_mock_source_sets_checked':len(inventory),
        'packet_report_scope':'Recorded local IPv4 namespace evidence only; not rerun by this check',
        'recorded_packet_observations':packet.get('passed'),
        'recorded_dns_wire_tests':dns_report.get('passed'),
        'recorded_native_readback_cases':native_report.get('passed'),
        'tested_source_files_checked':len(snapshot),
        'unchanged_native_source_files_checked':retained_native,
        'issues':issues,'terraform_validation':'NOT_PERFORMED_BY_PACKAGE_CHECK',
        'live_infrastructure_qualification':'NOT_RUN',
        'scope':'Local package integrity, new links and result consistency. Historical documents and workbooks were preserved, not newly rendered or recalculated.',
    }
    (ROOT/'quality/package_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if not issues else 1


if __name__=='__main__': raise SystemExit(main())
