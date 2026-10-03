'use strict';
const assert = require('node:assert/strict');
const {test} = require('node:test');
const {spawnSync} = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '../../..');
const UI = require(path.join(root, 'provisioner/controlplane/api/portal/application_drafts.js'));
const run = spawnSync(process.env.PYTHON || 'python', ['-c',
  'import json; from tests.provisioning.api.test_application_review_browser_assets import review_fixtures; print(json.dumps(review_fixtures()))'],
  {cwd:root, encoding:'utf8', timeout:20000});
assert.equal(run.status, 0, run.stderr);
const fixtures = JSON.parse(run.stdout), sample = fixtures.variants.find(v=>v.review.status==='REVIEWED_ASSESSMENT_ONLY');
const clone = v => JSON.parse(JSON.stringify(v));
const response = (v,status=200,headers={})=>new Response(JSON.stringify(v),{status,headers:{'Content-Type':'application/json',...headers}});
class Element {
  constructor(tag=''){this.tag=tag;this.children=[];this.listeners={};this.value='';this.textContent='';this.disabled=false;this.hidden=false;this.checked=false;}
  replaceChildren(...v){this.children=v;this.textContent='';}
  append(...v){this.children.push(...v);}
  addEventListener(k,fn){(this.listeners[k]??=[]).push(fn);}
  async fire(k){for(const fn of this.listeners[k]??[])await fn({preventDefault(){},target:this});}
}
function deferred(){let resolve;const promise=new Promise(r=>{resolve=r;});return {promise,resolve};}
function harness({row=sample,handler=null,clock=()=>100,timeoutMs=15000}={}) {
  const elements=new Map(),events={},docEvents={},calls=[],timers=new Map(),selections=[];
  const el=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
  const document={hidden:false,getElementById:el,createElement:t=>new Element(t),addEventListener:(k,fn)=>docEvents[k]=fn};
  let auth={token:'synthetic-reader',version:1},sequence=0,rejected=0;
  const client=UI.mount({document,session:()=>auth,clock,timeoutMs,
    fetch:async(url,init)=>{calls.push([url,init]);return handler ? handler(url,init) : response(url.includes('/review?')?row.review:row.record);},
    window:{addEventListener:(k,fn)=>events[k]=fn},onSelection:v=>selections.push(v),
    schedule:(fn,delay)=>{const id=++sequence;timers.set(id,{fn,delay});return id;},cancel:id=>timers.delete(id),
    rejectSession:()=>{rejected++;auth={token:null,version:auth.version+1};client.clear();}});
  const $=id=>el('draft-'+id);
  $('environment').value=row.record.environmentId;$('group').value=row.record.applicationGroupId;
  const check=async()=>{await client.load();await $('review-check').fire('click');};
  return {client,$,calls,events,docEvents,document,timers,selections,check,rejected:()=>rejected,
    setAuth:v=>auth=v,setRow:()=>{$('environment').value=row.record.environmentId;$('group').value=row.record.applicationGroupId;},
    hide:()=>{document.hidden=true;docEvents.visibilitychange();}};
}
for(const row of fixtures.variants) test(`real service status ${row.review.status} is displayed without mutation`,async()=>{
  const h=harness({row});await h.check();
  assert.equal(h.$('review-result').hidden,false);assert.ok(h.$('review-result').textContent.startsWith(row.review.status));
  assert.ok(h.$('review-result').textContent.includes(row.review.draftRecordDigest));
  assert.ok(h.$('review-result').textContent.includes(row.review.checkedAt));
  assert.match(h.$('review-result').textContent,/Execution authorized: false/);
  assert.equal(h.calls.length,2);assert.ok(h.calls.every(v=>v[1].method==='GET'&&!Object.hasOwn(v[1],'body')));
  assert.equal(row.record.status,'UNREVIEWED');
  if(row.review.status.startsWith('HELD_SUPERSEDED')) {
    assert.equal(h.client.selection(),null);assert.equal(h.$('edit-evidence').disabled,true);
  }
});
test('actual authenticated HTTP export and review use exactly one pinned GET',async()=>{
  const row=fixtures.api,h=harness({row});await h.check();
  assert.equal(h.$('review-result').hidden,false);
  const [url,init]=h.calls[1];
  assert.equal(url,`/v1/environments/${row.record.environmentId}/application-drafts/${row.record.applicationGroupId}/review?revision=${row.record.revision}`);
  assert.equal(init.method,'GET');assert.equal(init.cache,'no-store');assert.equal(init.mode,'same-origin');
  assert.equal(init.redirect,'error');assert.equal(init.credentials,'omit');assert.equal(init.referrerPolicy,'no-referrer');
  assert.equal(init.headers.Authorization,'Bearer synthetic-reader');assert.equal(init.body,undefined);
});
test('all source identity and evidence pins are checked against the full loaded draft',()=>{
  for(const field of ['environmentId','applicationGroupId','draftRecordDigest','proposalDigest','resultDigest']) {
    const value=clone(sample.review);value[field]='a'.repeat(64);assert.throws(()=>UI.validateReview(value,sample.record),undefined,field);
  }
  for(const field of ['draftRevision','generation','latestGeneration','latestDraftRevision','evidenceRevision']) {
    for(const bad of [true,0,-1,'1',Number.MAX_SAFE_INTEGER+1]) {
      const value=clone(sample.review);value[field]=bad;assert.throws(()=>UI.validateReview(value,sample.record),undefined,field);
    }
  }
  for(const field of Object.keys(sample.record.scope)) {
    const value=clone(sample.review);value.scope[field]='foreign';assert.throws(()=>UI.validateReview(value,sample.record));
  }
});
test('missing extra authority and malformed digest fields cannot produce review advice',()=>{
  for(const field of Object.keys(sample.review)) {
    const value=clone(sample.review);delete value[field];assert.throws(()=>UI.validateReview(value,sample.record));
  }
  for(const field of ['ownershipAccepted','executionAuthorized','dependencyEvidenceVerified']) {
    const value=clone(sample.review);value[field]=true;assert.throws(()=>UI.validateReview(value,sample.record));
  }
  for(const bad of ['F'.repeat(64),'a'.repeat(63),['a'.repeat(64)],null]) {
    const value=clone(sample.review);value.evidenceDigest=bad;assert.throws(()=>UI.validateReview(value,sample.record));
  }
  assert.throws(()=>UI.validateReview({...sample.review,signature:'untrusted'},sample.record));
});
test('owner must match proposed owner and cannot equal recorded editor',()=>{
  assert.throws(()=>UI.validateReview({...sample.review,ownerId:'someone-else'},sample.record));
  assert.throws(()=>UI.validateReview(sample.review,{...sample.record,recordedBy:sample.review.ownerId}));
});
test('timestamps retain microseconds and cannot normalize invalid calendar or lifetime',()=>{
  const base=clone(sample.review);
  base.reviewedAt='2026-10-01T12:00:00.000001Z';base.checkedAt='2026-10-01T12:00:00.000002Z';base.expiresAt='2026-10-01T13:00:00.000001Z';
  assert.equal(UI.validateReview(base,sample.record),true);
  for(const [key,bad] of [['checkedAt',base.expiresAt],['checkedAt',base.reviewedAt.replace('000001','000000')],
    ['expiresAt','2026-10-01T13:00:00.000002Z'],['reviewedAt','2026-02-30T12:00:00Z'],
    ['checkedAt','2026-10-01T12:00:00-04:00'],['checkedAt','2026-10-01'],['checkedAt','2026-10-01T12:00:00.1234567Z']]) {
    assert.throws(()=>UI.validateReview({...base,[key]:bad},sample.record),undefined,key+' '+bad);
  }
});
test('status priority candidate and unknown counts cannot contradict the original record',()=>{
  for(const change of [v=>v.ownerDecision='REVOKE',v=>v.status='APPROVED',v=>v.candidateDigest=null,
    v=>v.unknownDependencyCount=1,v=>v.unknownDependencyCount=true,v=>v.latestDraftRevision++,v=>v.latestGeneration++]) {
    const v=clone(sample.review);change(v);assert.throws(()=>UI.validateReview(v,sample.record));
  }
  const unknown=fixtures.variants.find(v=>v.review.status==='REVIEWED_WITH_UNKNOWNS');
  assert.throws(()=>UI.validateReview({...unknown.review,unknownDependencyCount:0},unknown.record));
  const empty=fixtures.variants[0];assert.throws(()=>UI.validateReview({...empty.review,ownerId:'owner-a'},empty.record));
  assert.throws(()=>UI.validateReview({...empty.review,candidateDigest:'b'.repeat(64)},empty.record));
});
test('latest generation cannot regress from the already displayed source metadata',()=>{
  const row=fixtures.variants.find(v=>v.review.status==='HELD_SUPERSEDED_INVENTORY');
  const record={...clone(row.record),latestGeneration:3,sourceSuperseded:true};
  assert.throws(()=>UI.validateReview(row.review,record));
});
test('historical and superseded records can inspect review without becoming writable',async()=>{
  const row=clone(fixtures.variants.find(v=>v.review.status==='HELD_SUPERSEDED_INVENTORY'));
  row.record.latestGeneration=2;row.record.sourceSuperseded=true;
  const h=harness({row});h.$('revision').value=String(row.record.revision);await h.check();
  assert.equal(h.$('review-result').hidden,false);assert.equal(h.$('name').disabled,true);assert.equal(h.client.selection(),null);
});
test('unsigned local changes cannot trigger a saved-review request and clear old advice',async()=>{
  const h=harness();await h.check();h.$('name').value='New name';await h.$('name').fire('input');
  assert.equal(h.$('review-result').hidden,true);assert.equal(h.$('review-result').textContent,'');assert.equal(h.timers.size,0);
  await h.client.checkReview();assert.equal(h.calls.length,2);assert.equal(h.$('review-check').disabled,true);
});
test('explicit structural editing clears review even when its source check fails',async()=>{
  const h=harness({handler:url=>response(url.endsWith('/latest')?{}:url.includes('/review?')?sample.review:sample.record)});
  await h.check();await h.client.editEvidence();assert.equal(h.$('review-result').hidden,true);
  assert.equal(h.$('review-result').textContent,'');assert.equal(h.timers.size,0);
});
test('failed refreshed review cannot leave an earlier accepted status visible',async()=>{
  let count=0;const h=harness({handler:url=>url.includes('/review?')?response(++count===1?sample.review:{error:'private'},count===1?200:503):response(sample.record)});
  await h.check();await h.client.checkReview();assert.equal(h.$('review-result').hidden,true);
  assert.match(h.$('review-status').textContent,/No earlier review/);assert.equal(h.calls.length,3);assert.equal(h.timers.size,0);
});
test('read failure malformed JSON and wrong origin contract are never shown or retried',async()=>{
  for(const answer of [()=>response(sample.review,404),()=>response(sample.review,503),()=>response(sample.review,202),
    ()=>response(sample.review,200,{'Content-Type':'text/html'}),()=>response(sample.review,200,{'Content-Length':'524289'}),
    ()=>response(sample.review,200,{'Content-Length':'1'}),
    ()=>new Response('{"format":1,"format":2}',{headers:{'Content-Type':'application/json'}}),
    ()=>new Response(new Uint8Array([255]),{headers:{'Content-Type':'application/json'}}),
    ()=>new Response(' '.repeat(524289),{headers:{'Content-Type':'application/json'}})]) {
    const h=harness({handler:url=>url.includes('/review?')?answer():response(sample.record)});await h.check();
    assert.equal(h.$('review-result').hidden,true);assert.equal(h.calls.length,2);assert.equal(h.timers.size,0);
  }
});
test('HTTP authentication rejection clears the whole draft identity and review',async()=>{
  const h=harness({handler:url=>url.includes('/review?')?response({},401):response(sample.record)});await h.check();
  assert.equal(h.rejected(),1);assert.equal(h.$('review-result').textContent,'');assert.equal(h.$('binding').textContent,'');
});
test('clear and new identities suppress late review responses',async()=>{
  const wait=deferred(),h=harness({handler:url=>url.includes('/review?')?wait.promise:response(sample.record)});
  await h.client.load();const pending=h.client.checkReview();await new Promise(setImmediate);
  h.setAuth({token:'different-reader',version:2});h.client.clear();wait.resolve(response(sample.review));await pending;
  assert.equal(h.$('review-result').hidden,true);assert.equal(h.$('review-result').textContent,'');assert.equal(h.timers.size,0);
});
test('changing saved selections clears the exact prior review',async()=>{
  for(const name of ['environment','group','revision']) {
    const h=harness();await h.check();h.$(name).value='different';await h.$(name).fire('input');
    assert.equal(h.$('review-result').hidden,true);assert.equal(h.timers.size,0);assert.equal(h.client.selection(),null);
  }
});
test('review display has a conservative 60-second cap and uses remaining server validity',async()=>{
  const h=harness();await h.check();assert.equal([...h.timers.values()][0].delay,60000);
  assert.equal(UI.reviewDisplayMilliseconds({checkedAt:'2026-10-01T12:00:00.000001Z',expiresAt:'2026-10-01T12:00:02.000001Z'},150),1850);
  for(const elapsed of [Infinity,NaN,-1,60000])assert.throws(()=>UI.reviewDisplayMilliseconds(sample.review,elapsed));
  const entry=[...h.timers.values()][0];entry.fn();assert.equal(h.$('review-result').hidden,true);
  assert.match(h.$('review-status').textContent,/expired/);assert.equal(h.calls.length,2);assert.equal(h.timers.size,0);
});
test('network time consumes the display budget and expired arrivals are not rendered',async()=>{
  for(const elapsed of [-1,60000,NaN]) {
    let n=0;const h=harness({clock:()=>n++?100+elapsed:100});await h.check();
    assert.equal(h.$('review-result').hidden,true);assert.equal(h.timers.size,0);
  }
});
test('hiding a tab clears review without a new request or erasing the loaded draft',async()=>{
  const h=harness();await h.check();h.hide();assert.equal(h.$('review-result').hidden,true);assert.equal(h.timers.size,0);
  assert.ok(h.$('binding').textContent.includes(sample.record.environmentId));assert.equal(h.calls.length,2);
  await h.client.checkReview();assert.equal(h.calls.length,2);
  h.document.hidden=false;await h.client.checkReview();assert.equal(h.calls.length,3);
});
test('hiding during a review aborts just that read and suppresses the late reply',async()=>{
  const wait=deferred(),h=harness({handler:url=>url.includes('/review?')?wait.promise:response(sample.record)});
  await h.client.load();const pending=h.client.checkReview();await new Promise(setImmediate);h.hide();
  assert.equal(h.calls[1][1].signal.aborted,true);wait.resolve(response(sample.review));await pending;
  assert.equal(h.$('review-result').hidden,true);assert.equal(h.$('review-check').disabled,false);
  assert.ok(h.$('binding').textContent.includes(sample.record.applicationGroupId));
});
test('hiding during a draft save preserves its uncertain-write reconciliation',async()=>{
  const wait=deferred(),h=harness({handler:(_url,init)=>init.method==='PUT'?wait.promise:response(sample.record)});
  await h.client.load();h.$('name').value='Edited';await h.$('name').fire('input');h.$('confirm').checked=true;
  const pending=h.client.save();await new Promise(setImmediate);h.hide();
  assert.equal(h.calls[1][1].signal.aborted,false);wait.resolve(response({},503));await pending;
  assert.match(h.$('status').textContent,/SAVE UNKNOWN/);assert.equal(h.$('reconcile').hidden,false);
  await h.client.checkReview();assert.equal(h.calls.length,2);
});
test('read deadline aborts its body and reports no review without retry',async()=>{
  let aborted=false;
  const h=harness({timeoutMs:15,handler:(url,init)=>!url.includes('/review?')?response(sample.record):
    new Response(new ReadableStream({start(stream){init.signal.addEventListener('abort',()=>{aborted=true;stream.error(Error('timeout'));});}}),{headers:{'Content-Type':'application/json'}})});
  await h.check();assert.equal(aborted,true);assert.equal(h.$('review-result').hidden,true);assert.equal(h.calls.length,2);
});
test('review scope and record labels render as text rather than injected markup',async()=>{
  const row=clone(sample),label='<img src=x onerror=alert(1)>';
  row.record.scope.native_scope_id=label;row.record.proposal.scope.native_scope_id=label;row.review.scope.native_scope_id=label;
  row.record.proposal.draft.members.forEach(m=>m.nativeVm[1]=label);
  const h=harness({row});await h.check();assert.equal(h.$('review-result').hidden,false);
  assert.ok(h.$('review-result').textContent.includes(label));assert.equal(h.$('review-result').innerHTML,undefined);
});
test('comparison calls the single review validator and cannot silently use retired code',()=>{
  const Comparison=require(path.join(root,'provisioner/controlplane/api/portal/application_comparison.js'));
  const original=UI.validateReview;let invoked=0;
  UI.validateReview=()=>{invoked++;throw Error('shared validator');};
  const record=fixtures.api.record;
  const value={format:'hosting-application-comparison/2',selectionDigest:'a'.repeat(64),applicationReview:fixtures.api.review,
    sourceInput:null,destinationInputs:[],assessments:[],status:'HELD_APPLICATION_REVIEW',consistency:'PINNED_INPUTS_LIVE_RECHECKS',
    ownershipAccepted:false,executionAuthorized:false,dependencyEvidenceVerified:false,reservationHeld:false};
  try{assert.throws(()=>Comparison.validateReport(value,{},'a'.repeat(64),record),/shared validator/);assert.equal(invoked,1);}
  finally{UI.validateReview=original;}
});
test('page exit removes review and cannot retain candidate status across navigation',async()=>{
  const h=harness();await h.check();h.events.pagehide();assert.equal(h.$('review-result').textContent,'');assert.equal(h.timers.size,0);
});

test('an unreviewed status cannot predate its immutable saved record',()=>{
  const row=fixtures.variants[0];
  assert.throws(()=>UI.validateReview({...row.review,checkedAt:'2020-01-01T00:00:00Z'},row.record));
});
test('signed-out or unloaded review actions make no request',async()=>{
  const h=harness();await h.client.checkReview();assert.equal(h.calls.length,0);
  await h.client.load();h.setAuth({token:null,version:2});await h.client.checkReview();
  assert.equal(h.calls.length,1);assert.match(h.$('review-status').textContent,/Sign in/);
});
