#!/usr/bin/env python3
"""P03 exact-source PostgreSQL campaign in an explicitly disposable CI service."""
import argparse,datetime,hashlib,json,os,re,secrets,subprocess,tempfile,time
from pathlib import Path
import xml.etree.ElementTree as ET

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('P03_TEST_POSTGRES')!='1':p.error('Requires the disposable P03 CI database.')
 root=Path(__file__).resolve().parents[2];out=a.output;out.mkdir(parents=True,exist_ok=False)
 report={'result':'RUNNING','source_revision':os.environ['GITHUB_SHA'],'observed_at':datetime.datetime.now(datetime.UTC).isoformat(),'commands':[],
         'limitations':['Synthetic authorities in Catalogue feature suite; live Governance/Console wire integration is a distinct campaign.','No operated deployment, native qualification, manual accessibility or independent G03 receiving review.']}
 paths=subprocess.check_output(['git','ls-files'],cwd=root,text=True).splitlines()
 report['source_sha256']={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in paths if n.startswith(('services/catalogue/','services/governance/','scripts/p03/','contracts/','.github/workflows/p03'))}
 private_values=[os.environ['P03_ADMIN_PASSWORD']];pg_env=os.environ|{'PGHOST':'127.0.0.1','PGPORT':'5432','PGUSER':'postgres','PGPASSWORD':private_values[0]}
 def redact(s):
  for value in private_values:s=s.replace(value,'[REDACTED]')
  return s
 def run(label,args,cwd=root,env=None,input=None):
  v=subprocess.run(args,cwd=cwd,env=env,input=input,text=True,capture_output=True,timeout=150)
  body=redact(v.stdout+v.stderr);(out/(label+'.log')).write_text(body)
  report['commands'].append({'name':label,'exit_code':v.returncode,'log':label+'.log','sha256':hashlib.sha256(body.encode()).hexdigest()})
  if v.returncode:raise RuntimeError(label+' failed')
  return v.stdout
 def sql(label,s):return run(label,['psql','-X','-v','ON_ERROR_STOP=1','-A','-t','-d','p03_catalogue_test'],env=pg_env,input=s)
 try:
  with tempfile.TemporaryDirectory(prefix='p03-private-') as tmp:
   private=Path(tmp);crt=private/'postgres.crt';key=private/'postgres.key'
   run('create-disposable-tls',['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(crt),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=IP:127.0.0.1,DNS:localhost'])
   container=os.environ['P03_POSTGRES_CONTAINER']
   if not re.fullmatch('[0-9a-f]{64}',container):raise ValueError('Invalid disposable container identity')
   run('tls-directory',['docker','exec',container,'mkdir','-p','/tmp/p03-tls'])
   for path in [crt,key]:run('copy-'+path.name,['docker','cp',str(path),container+':/tmp/p03-tls/'+path.name])
   run('tls-owner',['docker','exec',container,'chown','-R','postgres:postgres','/tmp/p03-tls'])
   run('tls-mode',['docker','exec',container,'chmod','0600','/tmp/p03-tls/postgres.key'])
   sql('enable-tls',"ALTER SYSTEM SET ssl_cert_file='/tmp/p03-tls/postgres.crt'; ALTER SYSTEM SET ssl_key_file='/tmp/p03-tls/postgres.key'; ALTER SYSTEM SET ssl='on'; SELECT pg_reload_conf();")
   pg_env.update(PGSSLMODE='verify-full',PGSSLROOTCERT=str(crt));time.sleep(.3)
   if sql('tls-readback','SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid();').strip()!='t':raise ValueError('TLS not verified')
   password=secrets.token_hex(32);private_values.append(password)
   sql('test-roles',f"CREATE ROLE catalogue_owner NOLOGIN; CREATE ROLE catalogue_runtime LOGIN PASSWORD '{password}';")
   env=os.environ|{'P03_PGHOST':'127.0.0.1','P03_PGPORT':'5432','P03_RUNTIME_PASSWORD':password,'P03_SSLMODE':'verify-full','P03_SSLROOTCERT':str(crt)}
   run('catalogue-postgresql',['php','vendor/bin/pest','--colors=never','--fail-on-warning','--fail-on-risky','--fail-on-empty-test-suite','--log-junit',str(out/'catalogue-junit.xml')],cwd=root/'services/catalogue',env=env)
   suites=ET.parse(out/'catalogue-junit.xml').getroot(); tests=list(suites.iter('testcase'))
   if len(tests)<80 or any(t.find(tag) is not None for t in tests for tag in ['skipped','failure','error']):raise ValueError('Required cases missing/skipped/failed')
   report['catalogue_tests']=len(tests)
   for component in ['catalogue','governance']:
    for gate in ['test:format','test:types','test:architecture']:
     run(component+'-'+gate.replace(':','-'),['composer',gate],cwd=root/'services'/component)
   report['result']='PASS'
 except Exception as e:report['result']='FAIL';report['error']=redact(str(e))
 report['source_unchanged']=all(hashlib.sha256((root/n).read_bytes()).hexdigest()==v for n,v in report['source_sha256'].items())
 if not report['source_unchanged']:report['result']='FAIL'
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['result','source_revision']}));return 0 if report['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
