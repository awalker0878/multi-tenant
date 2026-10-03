'use strict';
const assert = require('node:assert/strict');
const {test} = require('node:test');
const {spawnSync} = require('node:child_process');
const {webcrypto} = require('node:crypto');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const root = path.resolve(__dirname, '../../..'), portal = path.join(root, 'provisioner/controlplane/api/portal');
const Drafts = require(path.join(portal, 'application_drafts.js'));
const UI = require(path.join(portal, 'application_comparison.js'));
const copy = (v) => JSON.parse(JSON.stringify(v));
// Use the actual API and application service with independently signed fixtures.
// No PostgreSQL, native platform, mutation or external HTTP is involved.
const generated = spawnSync(process.env.PYTHON || 'python', ['-c', `
import json
from tests.provisioning.api.test_application_assessment_http import ApplicationAssessmentHttpTests
f = ApplicationAssessmentHttpTests(); f.setUp()
try:
    def read():
        r = f.client.post('/v1/assessments/applications/compare', json=f.body,
                          headers={'Authorization':'Bearer operator'})
        assert r.status_code == 200, r.text
        return r.json()
    value = {'request': f.body, 'record': f.fixture.stored.document(latest_generation=7), 'report': read()}
    f.fixture.reviews.none = True
    value['held'] = read()
    print(json.dumps(value))
finally:
    f.doCleanups()
`], {cwd: root, encoding: 'utf8', timeout: 20000});
assert.equal(generated.status, 0, generated.stderr);
const sample = JSON.parse(generated.stdout);
const profiles = () => new Map(sample.request.memberProfiles.map((m) => [m.workloadId, m.guestProfile]));
const settings = () => ({method:sample.request.method,networkMode:sample.request.networkMode,dataMode:sample.request.dataMode});
const compose = (r=sample.record,p=profiles(),d=sample.request.destinations,s=settings()) => UI.buildRequest(r,p,d,s);
const valid = (v) => UI.validateReport(v,sample.request,sample.report.selectionDigest,sample.record);
function response(value,status=200,headers={}) { return new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json',...headers}}); }
class Element {
  constructor(tag=''){this.tag=tag;this.children=[];this.listeners={};this.value='';this.textContent='';this.checked=false;this.hidden=false;this.disabled=false;}
  replaceChildren(...v){this.children=v;this.textContent='';}
  append(...v){this.children.push(...v);}
  addEventListener(name,fn){(this.listeners[name]??=[]).push(fn);}
  async fire(name){for(const fn of this.listeners[name]??[])await fn({preventDefault(){},target:this});}
}
function deferred(){let resolve;const promise=new Promise((r)=>{resolve=r;});return {promise,resolve};}
function harness(handler=()=>response(sample.report),options={}) {
  const elements=new Map(),created=[],calls=[],events={};
  const el=(id)=>{if(!elements.has(id))elements.set(id,new Element(id));return elements.get(id);};
  let auth={token:'synthetic-token',version:1},selected=copy(sample.request.destinations),route=settings(),rejected=0;
  const client=UI.mount({document:{getElementById:el,createElement:(tag)=>{const e=new Element(tag);created.push(e);return e;}},
    window:{addEventListener:(key,fn)=>{events[key]=fn;}},drafts:Drafts,session:()=>auth,
    destinations:()=>selected,settings:()=>route,fetch:async(url,init)=>{calls.push([url,init]);return handler(url,init);},
    rejectSession:()=>{rejected++;auth={token:null,version:auth.version+1};},...options});
  const $=(id)=>el('app-compare-'+id);
  client.setSource(copy(sample.record));
  const inputs=()=>$('members').children.map((row)=>row.children[2].children[1]);
  const fill=async()=>{for(const input of inputs()){input.value='linux-uefi';await input.fire('input');}};
  return {client,$,calls,events,created,fill,inputs,setAuth:(v)=>{auth=v;},auth:()=>auth,
    rejected:()=>rejected,setTargets:(v)=>{selected=v;client.invalidate();},setRoute:(v)=>{route=v;client.invalidate();}};
}
test('request uses the retained complete draft, explicit profiles and original target pins',()=>{
  assert.deepEqual(compose(),sample.request);
  assert.equal(compose().draftRecordDigest,sample.record.recordDigest);
  const r=copy(sample.record); r.sourceSuperseded=true; assert.throws(()=>compose(r));
});
test('selection digest matches the actual version-2 API response',async()=>{
  assert.equal(await UI.selectionDigest(compose()),sample.report.selectionDigest);
  const body=compose();body.destinations[0].capacityNativeId='pool-é-😀';
  const py=spawnSync(process.env.PYTHON||'python',['-c',
    'import json,hashlib,sys; print(hashlib.sha256(json.dumps(json.load(sys.stdin),sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("ascii")).hexdigest())'],
    {input:JSON.stringify(body),encoding:'utf8',timeout:5000});
  assert.equal(await UI.selectionDigest(body),py.stdout.trim());
});
test('invalid, omitted, duplicated or excessive selections are refused before requests',()=>{
  for(const modify of [d=>d.push(d[0]),d=>d[0].environmentId=sample.record.environmentId,
    d=>d[0].generation=true,d=>d[0].capacityKind='invented',d=>d[0].capacityNativeId='',d=>d.pop()]){
    const d=copy(sample.request.destinations);modify(d);assert.throws(()=>compose(sample.record,profiles(),d));
  }
  const p=profiles();p.delete('web');assert.throws(()=>compose(sample.record,p));
  p.set('web','bad profile');assert.throws(()=>compose(sample.record,p));
  const r=copy(sample.record);r.proposal.draft.members=Array.from({length:101},(_,i)=>({workloadId:'w'+i}));
  assert.throws(()=>compose(r));
  const r2=copy(sample.record);r2.proposal.draft.members=Array.from({length:100},(_,i)=>({workloadId:'w'+i}));
  assert.throws(()=>compose(r2,new Map(r2.proposal.draft.members.map(m=>[m.workloadId,'linux'])),
    [...sample.request.destinations,{environmentId:'third',generation:7}]));
});
test('real assessed and held service responses pass without changing their authority',()=>{
  assert.equal(valid(sample.report),sample.report);assert.equal(valid(sample.held),sample.held);
  assert.equal(sample.report.reservationHeld,false);
});
test('wrong interpretations, selections, flags and signed review bindings are refused',()=>{
  for(const change of [v=>v.format='hosting-application-comparison/1',v=>v.selectionDigest='f'.repeat(64),
    v=>v.executionAuthorized=true,v=>v.ownershipAccepted=true,v=>v.reservationHeld=true,
    v=>v.dependencyEvidenceVerified=true,v=>v.applicationReview.scope.tenant_id='other',
    v=>v.applicationReview.draftRecordDigest='f'.repeat(64),v=>v.applicationReview.ownerId='other',
    v=>v.applicationReview.evidenceDigest=null,v=>v.applicationReview.expiresAt=v.applicationReview.checkedAt,
    v=>v.applicationReview.ownerDecision='REVOKE',v=>v.applicationReview.latestDraftRevision++]){
    const v=copy(sample.report);change(v);assert.throws(()=>valid(v));
  }
});
test('a held review cannot smuggle partial destination findings',()=>{
  const v=copy(sample.held);v.assessments=sample.report.assessments;assert.throws(()=>valid(v));
});
test('membership profiles startup order and datasets remain exactly bound to the saved draft',()=>{
  for(const change of [v=>v.assessments[0].members.pop(),v=>v.assessments[0].members.push(v.assessments[0].members[0]),
    v=>v.assessments[0].members[0].guestProfile='different',v=>v.assessments[0].members[0].nativeVm[4]='foreign',
    v=>v.startupOrder.reverse(),v=>v.datasetCount++,v=>v.consistencyGroupCount++]){
    const v=copy(sample.report);change(v);assert.throws(()=>valid(v));
  }
});
test('foreign reordered and substituted targets or pools cannot be displayed',()=>{
  for(const change of [v=>v.destinationInputs.reverse(),v=>v.assessments.reverse(),v=>v.assessments.pop(),
    v=>v.destinationInputs[0].generation++,v=>v.assessments[0].capacityIdentity[4]='other',
    v=>v.sourceInput.observation.normalizerVersion='hosting-assessment-normalizer/1']){
    const v=copy(sample.report);change(v);assert.throws(()=>valid(v));
  }
});
test('capacity shortages and required reservation conditions cannot be omitted',()=>{
  const v=copy(sample.report);v.assessments[0].capacity.resources.VCPU.available=6;assert.throws(()=>valid(v));
  v.assessments[0].issues.push({severity:'BLOCKER',code:'APPLICATION_VCPU_CAPACITY_INSUFFICIENT'});
  v.assessments[0].status='BLOCKED';assert.equal(valid(v),v);
  for(const change of [r=>r.capacity.reservationHeld=true,r=>r.capacity.transientAndRecoveryFootprintIncluded=true,
    r=>r.capacity.resources.MEMORY.available=null,r=>r.capacity.resources.STORAGE.required=true,
    r=>r.issues=[],r=>{r.members[0].status='ELIGIBLE';r.members[0].issues.push({severity:'BLOCKER',code:'GAP'});}]){
    const r=copy(sample.report);change(r.assessments[0]);assert.throws(()=>valid(r));
  }
});
test('unknown dependency counts cannot be changed into an accepted empty set',()=>{
  const v=copy(sample.report);v.applicationReview.status='REVIEWED_WITH_UNKNOWNS';v.applicationReview.unknownDependencyCount=1;
  assert.throws(()=>valid(v));
});
test('microsecond ordering does not round a later member assessment into the review',()=>{
  const v=copy(sample.report),time=v.applicationReview.checkedAt.slice(0,19);
  v.applicationReview.checkedAt=time+'.000001+00:00';
  v.assessments[0].members[0].assessedAt=time+'.000002+00:00';assert.throws(()=>valid(v));
});
test('one bounded same-origin POST renders all destinations members and capacity',async()=>{
  const h=harness();await h.fill();assert.equal(h.$('submit').disabled,false);await h.client.compare();
  assert.equal(h.calls.length,1);assert.deepEqual(JSON.parse(h.calls[0][1].body),sample.request);
  assert.equal(h.calls[0][0],'/v1/assessments/applications/compare');
  for(const [key,value] of Object.entries({method:'POST',credentials:'omit',cache:'no-store',redirect:'error',mode:'same-origin'}))assert.equal(h.calls[0][1][key],value);
  assert.equal(h.$('results').hidden,false);assert.match(h.$('status').textContent,/2 members across 2/);
  assert.equal(h.created.filter(e=>e.tag==='details').length,4);
});
test('the real held response renders a hold without target cards',async()=>{
  const h=harness(()=>response(sample.held));await h.fill();await h.client.compare();
  assert.equal(h.$('results').hidden,false);assert.match(h.$('status').textContent,/review is held/);
  assert.equal(h.created.filter(e=>e.tag==='article').length,0);
});
test('missing profiles, missing current drafts and signed-out state send nothing',async()=>{
  const h=harness();await h.client.compare();assert.equal(h.calls.length,0);
  await h.fill();h.setAuth({token:null,version:2});await h.client.compare();assert.equal(h.calls.length,0);
  h.client.clear();assert.equal(h.$('submit').disabled,true);
});
test('changing a guest profile immediately removes earlier advice',async()=>{
  const h=harness();await h.fill();await h.client.compare();assert.equal(h.$('results').hidden,false);
  h.inputs()[0].value='other-profile';await h.inputs()[0].fire('input');assert.equal(h.$('results').hidden,true);
});
test('a double submission does not duplicate a calculation',async()=>{
  const started=deferred(),wait=deferred(),h=harness(()=>{started.resolve();return wait.promise;});await h.fill();
  const task=h.client.compare();await started.promise;await h.client.compare();assert.equal(h.calls.length,1);
  wait.resolve(response(sample.report));await task;
});
for(const what of ['destination','route','source','session','cancel','pagehide'])test(`late ${what}-superseded replies cannot restore cleared results`,async()=>{
  const started=deferred(),wait=deferred(),h=harness(()=>{started.resolve();return wait.promise;});await h.fill();
  const task=h.client.compare();await started.promise;
  if(what==='destination')h.setTargets([]);
  else if(what==='route')h.setRoute({...settings(),dataMode:'different'});
  else if(what==='source')h.client.setSource(null);
  else if(what==='session')h.setAuth({token:'another-person',version:2});
  else if(what==='cancel')await h.$('cancel').fire('click');
  else h.events.pagehide();
  wait.resolve(response(sample.report));await task;assert.equal(h.$('results').hidden,true);assert.equal(h.calls.length,1);
});
test('expired authentication clears retained source and does not retry',async()=>{
  const h=harness(()=>response({error:'denied'},401));await h.fill();await h.client.compare();
  assert.equal(h.rejected(),1);assert.equal(h.$('members').children.length,0);assert.equal(h.calls.length,1);
});
test('invalid HTTP, UTF-8, duplicate JSON and oversized bodies never render partial advice',async()=>{
  const good=JSON.stringify(sample.report);
  for(const fn of [()=>response(sample.report,202),()=>response(sample.report,403),
    ()=>response(sample.report,200,{'Content-Type':'text/html'}),
    ()=>new Response(good.replace('{','{"format":"bad",'),{headers:{'Content-Type':'application/json'}}),
    ()=>new Response(new Uint8Array([0xff]),{headers:{'Content-Type':'application/json'}}),
    ()=>new Response(' '.repeat(1048577),{headers:{'Content-Type':'application/json'}}),
    ()=>response(sample.report,200,{'Content-Length':'1048577'}),
    ()=>response(sample.report,200,{'Content-Length':'1'})]){
    const h=harness(fn);await h.fill();await h.client.compare();assert.equal(h.$('results').hidden,true);assert.equal(h.calls.length,1);
  }
});
test('strict parsing refuses unrepresentable integer quantities instead of rounding them',()=>{
  assert.throws(()=>Drafts.strictJson('{"capacity":9007199254740993}',1048576));
  assert.throws(()=>Drafts.strictJson(' '.repeat(524289)));
  assert.throws(()=>Drafts.strictJson('{}',1048577));
});
test('a blocked response header cancels its unread body',async()=>{
  let cancelled=false;
  const h=harness(()=>new Response(new ReadableStream({cancel(){cancelled=true;}}),{headers:{'Content-Type':'text/html'}}));
  await h.fill();await h.client.compare();assert.equal(cancelled,true);
});
test('body deadline aborts without rendering or automatic retry',async()=>{
  let aborted=false;
  const h=harness((url,init)=>new Response(new ReadableStream({start(stream){init.signal.addEventListener('abort',()=>{
    aborted=true;stream.error(Error('timeout'));});}}),{headers:{'Content-Type':'application/json'}}),{timeoutMs:25});
  await h.fill();await h.client.compare();assert.equal(aborted,true);assert.equal(h.$('results').hidden,true);assert.equal(h.calls.length,1);
});
test('remote strings are rendered as text, never inserted as markup',async()=>{
  const h=harness();const r=copy(sample.record);r.proposal.draft.members[0].nativeVm[4]='<img src=x onerror=alert(1)>';
  h.client.setSource(r);assert.equal(h.created.some(e=>e.tag==='img'),false);
  assert.ok(h.$('members').children[0].children[1].textContent.includes('<img'));
});
test('the real shell propagates draft edits destination changes and logout to the comparison',async()=>{
  const elements=new Map(),el=(id)=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
  const origin='https://mobility.example.org',context=vm.createContext({document:{getElementById:el,createElement:(tag)=>new Element(tag)},
    window:{location:{origin},addEventListener(){}},Option:function(label,value){return {label,value};},
    Date,URL,crypto:webcrypto,btoa,TextEncoder,TextDecoder,AbortController,Response,setTimeout,clearTimeout,
    fetch:async(url)=>response(url==='/portal/config.json'?{origin,redirectUri:origin+'/portal/callback'}:
      url==='/v1/assessments/applications/compare'?sample.report:sample.record)});
  for(const file of ['application_drafts.js','application_comparison.js','app.js'])vm.runInContext(fs.readFileSync(path.join(portal,file),'utf8'),context);
  await new Promise(setImmediate);vm.runInContext('accessToken="synthetic-token";tokenVersion=1;',context);
  el('comparison-method').value=sample.request.method;el('comparison-network').value=sample.request.networkMode;el('comparison-data').value=sample.request.dataMode;
  vm.runInContext('comparisonDestinations='+JSON.stringify(sample.request.destinations),context);
  el('draft-environment').value=sample.record.environmentId;el('draft-group').value=sample.record.applicationGroupId;
  await el('draft-load').fire('click');assert.equal(el('app-compare-members').children.length,2);
  for(const row of el('app-compare-members').children){const input=row.children[2].children[1];input.value='linux-uefi';await input.fire('input');}
  await el('app-compare-form').fire('submit');assert.equal(el('app-compare-results').hidden,false);
  await el('comparison-network').fire('input');assert.equal(el('app-compare-results').hidden,true);
  el('draft-name').value='Edited';await el('draft-name').fire('input');assert.equal(el('app-compare-members').children.length,0);
  await el('clear-session').fire('click');assert.equal(el('app-compare-source').textContent,'No unchanged current draft is selected.');
});
