#!/usr/bin/env python3
"""Check complete exact-source local packet reports; NOT an evidence authenticator.

Reject missing, stale-source, blocked or incomplete results rather than accepting
only a PASS label. No target contact, deployment or native-service approval occurs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lab.ipv6_fixture import FIXTURE_SHA256, ROOT

SOURCES={
 4:('lab/run_namespace_lab.py','lab/worker.py','lab/mini_filter.c','lab/link_config.py','lab/mtls_fixture.py','lab/mtls_scenarios.py'),
 6:('lab/ipv6_fixture.py','lab/ipv6_worker.py','lab/run_ipv6_lab.py','lab/run_namespace_lab.py','lab/mtls_fixture.py')}
PROFILE={4:('LOCAL_NAMESPACE_PACKET_FIXTURE','PASSED_NAMESPACE_FIXTURE','PKT',47),
         6:('LOCAL_ROUTED_IPV6_PACKET_FIXTURE','PASSED_IPV6_FIXTURE','IP6',49)}


def validate(report:dict,family:int,source_root:Path=ROOT)->dict:
    kind,status,prefix,total=PROFILE[family]
    if not isinstance(report,dict) or report.get('kind')!=kind or report.get('status')!=status:
        raise ValueError('Campaign is missing, failed or blocked')
    for name,expected in (('passed',total),('failed',0),('namespace_count',17)):
        if type(report.get(name)) is not int or report[name]!=expected:raise ValueError('Incomplete or inconsistent campaign totals')
    if report.get('native_vendor_qualification')!='NOT_RUN' or report.get('original_namespace_configuration_unchanged') is not True:
        raise ValueError('Qualification or original-configuration boundary differs')
    if report.get('fixture_sha256')!=FIXTURE_SHA256 or 'error' in report:raise ValueError('Fixture or error state differs')
    checks=report.get('checks')
    if not isinstance(checks,list) or len(checks)!=total:raise ValueError('Missing campaign observations')
    for index,item in enumerate(checks,1):
        if (not isinstance(item,dict) or item.get('id')!=f'{prefix}-{index:03}' or item.get('status')!='PASS'
                or not isinstance(item.get('name'),str) or not item['name'] or not isinstance(item.get('observed'),dict)):
            raise ValueError('Observation order, status or supporting record differs')
    hashes=report.get('source_sha256')
    if not isinstance(hashes,dict) or set(hashes)!=set(SOURCES[family]):raise ValueError('Incomplete implementation identity')
    for name in SOURCES[family]:
        actual=hashlib.sha256((source_root/name).read_bytes()).hexdigest()
        if actual!=hashes[name]:raise ValueError('Report does not describe the current source')
    if family==6:
        before=report.get('original_configuration_sha256_before');after=report.get('original_configuration_sha256_after')
        if not isinstance(before,str) or not re.fullmatch('[0-9a-f]{64}',before) or before!=after:raise ValueError('Original configuration digest changed or missing')
        if report.get('native_apply')!='NOT_RUN':raise ValueError('Unexpected native action claim')
        mtu=checks[38]['observed']
        if (mtu.get('large',{}).get('success') is not True or mtu['large'].get('path_mtu')!=1280
                or mtu['large'].get('bytes_echoed')!=8192
                or mtu.get('after',{}).get('related_error',-1)<=mtu.get('before',{}).get('related_error',-1)):
            raise ValueError('Missing successful PMTU witness')
    return {'family':family,'observations':total,'source_identity':'CURRENT_FILES_MATCH',
            'status':'COMPLETE_SCOPED_LOCAL_REPORT','native_qualification':'NOT_RUN'}


def load(path:Path)->dict:
    with path.open('rb') as stream:raw=stream.read(2_000_001)
    if len(raw)>2_000_000:raise ValueError('Report exceeds bounded size')
    def pairs(items):
        out={}
        for key,value in items:
            if key in out:raise ValueError('Duplicate JSON key')
            out[key]=value
        return out
    def reject(value):raise ValueError('Non-finite JSON number')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=reject)


def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=ROOT/'build/reports');args=parser.parse_args()
    results=[]
    try:
        for family,name in ((4,'local_packet_lab.json'),(6,'local_ipv6_packet_lab.json')):
            results.append(validate(load(args.directory/name),family))
        output={'status':'PASSED_BOTH_SCOPED_FAMILY_REPORTS','campaigns':results,
                'limitations':['Counts are observations, not independent native acceptance assertions',
                               'Source hashes bind bytes, not execution authenticity or authorization']}
        code=0
    except (ValueError,OSError,KeyError,TypeError,IndexError) as exc:
        output={'status':'FAILED_OR_INCOMPLETE_CAMPAIGN_REPORT','reason':str(exc)};code=2
    args.directory.mkdir(parents=True,exist_ok=True)
    (args.directory/'routed_family_review.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2));return code

if __name__=='__main__':raise SystemExit(main())
