#!/usr/bin/env python3
"""Execute real loopback TCP/TSIG DNS transactions against a bounded test authority."""
from pathlib import Path
import argparse
import io
import hashlib
import json
import sys
import time
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests.test_dns_transactions import DNSWireTests,DNSInputTests


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',action='store_true')
    p.add_argument('--output',type=Path,default=ROOT/'build/reports/local_dns_transactions.json')
    a=p.parse_args()
    if not a.execute:p.error('Explicit --execute runs only loopback disposable test authority')
    observations=[]
    class Recorded(unittest.TextTestResult):
        def addSuccess(self,test):
            super().addSuccess(test);observations.append({'id':test.id(),'result':'PASS'})
        def addFailure(self,test,err):
            super().addFailure(test,err);observations.append({'id':test.id(),'result':'FAIL'})
        def addError(self,test,err):
            super().addError(test,err);observations.append({'id':test.id(),'result':'ERROR'})
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(DNSWireTests),
                             DNSInputTests('test_ptr_exact_reverse_wire')])
    stream=io.StringIO();start=time.monotonic()
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Recorded).run(suite)
    report={'kind':'ACTUAL_LOCAL_DNS_TRANSACTION_TESTS','status':'PASSED_LOCAL_WIRE_FIXTURE' if result.wasSuccessful() else 'FAILED',
            'scope':'Real TCP DNS QUERY/UPDATE and TSIG verification; disposable loopback test authority',
            'passed':len([x for x in observations if x['result']=='PASS']),'failed':len(result.failures)+len(result.errors),
            'elapsed_seconds':round(time.monotonic()-start,3),'observations':observations,
            'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
                             ('tools/dns_change.py','lab/dns_authority.py','lab/run_dns_lab.py','tests/test_dns_transactions.py')},
            'native_dns_product_qualification':'NOT_RUN','infrastructure_contact':'NONE',
            'limits':['The local authority is an implementation of this test subset, not BIND or a production DNS service',
                      'AAAA is a DNS data record, not proof of IPv6 transport or reachability',
                      'No DNSSEC, delegation/replication/cache propagation, GSS-TSIG or IPAM allocation',
                      'Forward and reverse are independent single-zone transactions, not a distributed transaction']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='observations'},indent=2))
    if not result.wasSuccessful():print(stream.getvalue(),file=sys.stderr)
    return 0 if result.wasSuccessful() else 2
if __name__=='__main__':raise SystemExit(main())
