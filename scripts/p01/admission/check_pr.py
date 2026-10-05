"""Run only from the PR's trusted base; fetch candidate objects as inert data."""
from __future__ import annotations
import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request
import urllib.error
from urllib.parse import urlparse

from policy import Denied, affected, review, need
from check_sources import validate_source
from exclusions import check_added_suppressions


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[3];args.output.mkdir(parents=True,exist_ok=False)
    event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text());pr=event['pull_request'];repo=event['repository']['full_name']
    report={'result':'HELD','scope':'Trusted-base read-only PR review; no candidate source execution','source_revision':pr['base']['sha']}
    def git(*argv):
        env=None
        if argv[0]=='fetch':
            credential=base64.b64encode(('x-access-token:'+os.environ['GH_TOKEN']).encode()).decode()
            env=os.environ | {'GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'http.extraheader','GIT_CONFIG_VALUE_0':'AUTHORIZATION: basic '+credential}
        return subprocess.run(['git',*argv],cwd=root,env=env,capture_output=True,check=True,timeout=30).stdout
    def data(sha,path,default=None):
        size=subprocess.run(['git','cat-file','-s',sha+':'+path],cwd=root,capture_output=True,timeout=10)
        if size.returncode:
            if default is not None:return default
            raise Denied('required_revision_file_missing:'+path)
        need(int(size.stdout)<=2*1024*1024,'oversized_policy_input')
        return json.loads(git('show',sha+':'+path))
    def api(path,body=None):
        payload=None if body is None else json.dumps(body).encode()
        req=urllib.request.Request('https://api.github.com/'+path,data=payload,headers={
            'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json',
            'X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=30) as response:
            raw=response.read(8*1024*1024+1);need(len(raw)<=8*1024*1024,'oversized_api_response');return json.loads(raw)
    def pages(path,key=None):
        result=[]
        for page in range(1,21):
            body=api(path+('&' if '?' in path else '?')+'per_page=100&page='+str(page));rows=body[key] if key else body
            result.extend(rows)
            if len(rows)<100:return result
        raise Denied('api_pagination_limit')
    def artifact_bytes(artifact_id):
        # Do not forward the GitHub bearer token through its signed storage redirect.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,req,fp,code,msg,headers,newurl):return None
        req=urllib.request.Request(f'https://api.github.com/repos/{repo}/actions/artifacts/{artifact_id}/zip',
                                   headers={'Authorization':'Bearer '+os.environ['GH_TOKEN']})
        try:
            with urllib.request.build_opener(NoRedirect).open(req,timeout=30) as response:
                raw=response.read(1024*1024+1)
        except urllib.error.HTTPError as redirect:
            need(redirect.code==302,'check_artifact_download_failed')
            location=redirect.headers['Location'];parsed=urlparse(location)
            need(parsed.scheme=='https' and parsed.hostname and not parsed.username and not parsed.password,'unsafe_artifact_redirect')
            with urllib.request.urlopen(urllib.request.Request(location),timeout=30) as response:
                raw=response.read(1024*1024+1)
        need(len(raw)<=1024*1024,'oversized_check_artifact');return raw
    try:
        need(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo),'invalid_repository')
        number=int(pr['number']);prefix=f'repos/{repo}/pulls/{number}'
        current=api(prefix);head=current['head']['sha'];base=current['base']['sha'];tested=current['merge_commit_sha']
        need(all(isinstance(s,str) and re.fullmatch(r'[0-9a-f]{40}',s) for s in (head,base,tested)),'unavailable_merge_revision')
        need(git('rev-parse','HEAD').decode().strip()==base==pr['base']['sha'],'trusted_base_changed')
        # No checkout, submodules, build or script from these fetched candidate objects.
        git('fetch','--no-tags','origin',head,tested)
        parents=git('show','-s','--format=%P',tested).decode().strip().split()
        paths=git('diff','--no-renames','--name-only','-z',base,head,'--').decode().rstrip('\0').split('\0')
        need(0<len(paths)<=10000,'invalid_change_inventory')
        base_components=data(base,'scripts/p01/candidates.json')['components'];head_components=data(head,'scripts/p01/candidates.json')['components']
        base_graph=data(base,'architecture/contract-consumers.json',{});head_graph=data(head,'architecture/contract-consumers.json',{})
        impact=affected(paths,base_components,head_components,base_graph,head_graph)
        policy=data(base,'release/review-policy.json');exceptions=data(base,'release/exceptions.json')['exceptions']
        # Proposed records are reviewed as policy changes; only previously admitted
        # base records can authorize a suppression in this candidate.
        proposed_exceptions=[e for e in data(head,'release/exceptions.json')['exceptions'] if e not in exceptions]
        active_exceptions=[e for e in exceptions if any(p in paths for p in e['paths'])]
        for path in paths:
            if path.startswith(('apps/','services/','workers/','packages/')) and Path(path).suffix in {'.py','.php','.ts','.tsx','.js','.jsx','.vue'}:
                def source_text(sha):
                    size=subprocess.run(['git','cat-file','-s',sha+':'+path],cwd=root,capture_output=True,timeout=10)
                    if size.returncode:return ''
                    need(int(size.stdout)<=2*1024*1024,'oversized_analysis_input')
                    return git('show',sha+':'+path).decode()
                check_added_suppressions(path,source_text(base),source_text(head),active_exceptions,head)
        checks=pages(f'repos/{repo}/commits/{head}/check-runs?filter=latest','check_runs')
        verified_checks=[]
        if policy['status']=='ACTIVE':
            for name in policy['required_checks']:
                matching=[c for c in checks if c['name']==name and c['app']['id']==policy['allowed_check_app_id'] and c['head_sha']==head]
                need(matching,'missing_required_check:'+name);check=max(matching,key=lambda c:c['id'])
                need(check['status']=='completed' and check['conclusion']=='success','required_check_not_success:'+name)
                job=api(f"repos/{repo}/actions/jobs/{check['id']}");run=api(f"repos/{repo}/actions/runs/{job['run_id']}")
                expected=policy['check_sources'][name]
                artifact_name=f"check-source-{expected['job']}-{run['id']}-{run['run_attempt']}"
                artifacts=pages(f"repos/{repo}/actions/runs/{run['id']}/artifacts",'artifacts')
                matches=[a for a in artifacts if a['name']==artifact_name];need(len(matches)==1,'missing_check_source:'+name)
                artifact=matches[0]
                binding=validate_source(artifact_bytes(artifact['id']),artifact,run,job,expected,repository=repo,
                                        name=name,head=head,base=base,tested=tested,number=number)
                verified_checks.append({'id':check['id'],'name':name,'app_id':check['app']['id'],'head_sha':head,
                                        'tested_sha':binding['source_revision'],'status':check['status'],'conclusion':check['conclusion'],
                                        'artifact_id':artifact['id'],'artifact_digest':artifact['digest'],'workflow_run_id':run['id']})
        reviews=pages(prefix+'/reviews')
        permissions={}
        for account_id,account in policy['accounts'].items():
            need(re.fullmatch(r'[A-Za-z0-9-]{1,39}',account['login']),'invalid_reviewer_login')
            p=api(f"repos/{repo}/collaborators/{account['login']}/permission")
            need(str(p['user']['id'])==account_id and p['user']['type']=='User','reviewer_account_id_changed');permissions[account_id]=p['permission']
        owner,name=repo.split('/');unresolved=0;cursor=None
        for _ in range(20):
            result=api('graphql',{'query':'query($owner:String!,$name:String!,$number:Int!,$cursor:String){repository(owner:$owner,name:$name){pullRequest(number:$number){reviewThreads(first:100,after:$cursor){nodes{isResolved}pageInfo{hasNextPage endCursor}}}}}',
                                  'variables':{'owner':owner,'name':name,'number':number,'cursor':cursor}})
            need(not result.get('errors'),'review_threads_unavailable');threads=result['data']['repository']['pullRequest']['reviewThreads']
            unresolved+=sum(not t['isResolved'] for t in threads['nodes'])
            if not threads['pageInfo']['hasNextPage']:break
            cursor=threads['pageInfo']['endCursor']
        else:raise Denied('review_thread_pagination_limit')
        after=api(prefix)
        snapshot={'repository':repo,'state':current['state'],'draft':current['draft'],'head_sha':head,'base_sha':base,
                  'tested_sha':tested,'tested_parents':parents,'head_after':after['head']['sha'],'base_after':after['base']['sha'],
                  'author_id':current['user']['id'],'permissions':permissions,'exceptions':active_exceptions,
                  'candidate_exceptions':proposed_exceptions,'unresolved_threads':unresolved,
                  'checks':verified_checks,
                  'reviews':[{'id':r['id'],'user_id':r['user']['id'],'login':r['user']['login'],'state':r['state'],'commit_id':r['commit_id']} for r in reviews]}
        (args.output/'snapshot.json').write_text(json.dumps(snapshot,indent=2)+'\n');report['impact']=impact;report['changed_paths']=paths
        report.update(review(policy,snapshot,paths,impact))
    except Exception as error:
        # Never include request headers, credentials or review-comment bodies.
        report['denial']=str(error) if isinstance(error,Denied) else type(error).__name__
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    return 0 if report['result']=='ADMITTED' else 1


if __name__=='__main__':raise SystemExit(main())
