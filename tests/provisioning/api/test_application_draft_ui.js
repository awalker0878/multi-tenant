'use strict';
const assert = require('node:assert/strict');
const {test} = require('node:test');
const path = require('node:path');
const UI = require(path.resolve(__dirname, '../../../provisioner/controlplane/api/portal/application_drafts.js'));
const clone = (v) => JSON.parse(JSON.stringify(v));
const scope = {organization_id:'org-a',tenant_id:'tenant-a',site_id:'site-a',security_domain_id:'wsd-a',
  endpoint_id:'vcenter-a',native_scope_id:'datacenter-a',platform_family:'vmware'};
function record() {
  const draft = {applicationGroupId:'app-a',name:'Application A',ownerId:'owner-a',
    members:['db','web'].map((id,i)=>({workloadId:id,nativeVm:['vcenter-a','datacenter-a','vmware','vm','vm-'+i]})),
    datasetIds:['data-db','data-web'],consistencyGroups:[{groupId:'all-data',datasetIds:['data-db','data-web']}],
    startupOrder:['db','web']};
  const dependencies = [
    {assertionId:'edge-a',sourceWorkloadId:'web',targetWorkloadId:'db',relation:'STARTS_AFTER',state:'KNOWN',
      source:'CMDB',sourceReference:'cmdb-a',observedAt:'2026-09-29T12:00:00.123456+00:00',unknownReason:null},
    {assertionId:'edge-b',sourceWorkloadId:'web',targetWorkloadId:null,relation:'SERVICE_CALL',state:'UNKNOWN',
      source:'MONITORING',sourceReference:'trace-a',observedAt:'2026-09-29T12:00:00+00:00',unknownReason:'EXTERNAL_DEPENDENCY'}];
  return {format:'hosting-application-draft-revision/1',environmentId:'env-a',scope:clone(scope),
    applicationGroupId:'app-a',revision:2,generation:3,resultDigest:'a'.repeat(64),proposalDigest:'b'.repeat(64),
    recordedBy:'editor@example.org',recordedAt:'2026-09-29T12:05:00+00:00',recordDigest:'c'.repeat(64),
    proposal:{format:'hosting-application-group-candidate/1',discoveryDigest:'a'.repeat(64),scope:clone(scope),draft,dependencies},
    status:'UNREVIEWED',latestGeneration:3,sourceSuperseded:false,ownershipAccepted:false,executionAuthorized:false};
}
function summary(row=record()) {
  const {proposal,...binding}=row;
  return {...binding,name:proposal.draft.name,ownerId:proposal.draft.ownerId,memberCount:2,datasetCount:2,
    dependencyCount:2,unknownDependencyCount:1};
}
function page(items=[summary()],nextAfter=null) {
  return {format:'hosting-application-draft-list/1',environmentId:'env-a',scope:clone(scope),latestGeneration:3,
    consistency:'LIVE_PAGE',items,nextAfter,executionAuthorized:false};
}
function ack(body) {
  const value=record(); value.revision=body.expectedRevision+1;
  value.generation=body.generation; value.resultDigest=body.resultDigest;
  value.proposal.draft=clone(body.draft); value.proposal.dependencies=clone(body.dependencies);
  return value;
}
function response(value,status=200,headers={}) {
  return new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json',...headers}});
}
class Element {
  constructor(){this.children=[];this.listeners={};this.value='';this.textContent='';this.checked=false;this.hidden=false;this.disabled=false;}
  replaceChildren(...values){this.children=values;this.textContent='';}
  append(...values){this.children.push(...values);}
  addEventListener(name,fn){this.listeners[name]=fn;}
  async fire(name){return this.listeners[name]?.({preventDefault(){},target:this});}
}
function harness(handler,options={}) {
  const elements=new Map(), events={},calls=[];
  const element=(id)=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
  let auth={token:'synthetic-tab-token',version:1};
  const fetch=async(url,init)=>{calls.push([url,init]);return handler(url,init);};
  let rejected=0;
  const client=UI.mount({document:{getElementById:element,createElement:()=>new Element()},
    session:()=>auth,fetch,window:{addEventListener:(key,fn)=>{events[key]=fn;}},
    rejectSession:()=>{rejected++;auth={token:null,version:auth.version+1};client.clear();},...options});
  const $=(id)=>element('draft-'+id);
  $('environment').value='env-a';$('group').value='app-a';
  async function edit(name='Edited name') {
    $('name').value=name;await $('name').fire('input');$('confirm').checked=true;await $('confirm').fire('change');
  }
  return {client,$,calls,events,edit,auth:()=>auth,rejected:()=>rejected,
    setAuth:(v)=>{auth=v;},select:()=>{$('environment').value='env-a';$('group').value='app-a';}};
}
function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};}

test('strict JSON rejects duplicate escaped keys, rounding, syntax errors and excessive depth',()=>{
  for(const value of ['{"a":1,"a":2}','{"a":1,"\\u0061":2}','{"a":1e999}',
    '{"a":9007199254740993}','{"a":1.00000000000000001}','{"a":1e0}',
    '{"a":true,}','{"a":01}','[1,]','{} trailing','"bad\nstring"','['.repeat(26)+'0'+']'.repeat(26)]) {
    assert.throws(()=>UI.strictJson(value),undefined,value);
  }
  assert.equal(UI.canonical(UI.strictJson('{"x":[true,false,null,-1,0],"s":"\\u0041"}')),'{"s":"A","x":[true,false,null,-1,0]}');
});
test('strict JSON does not assign prototype setters',()=>{
  const value=UI.strictJson('{"__proto__":{"polluted":true}}');
  assert.equal(Object.getPrototypeOf(value),null);assert.equal({}.polluted,undefined);
});
test('validated records reject wrong scope, source, authority, identity and added fields',()=>{
  assert.deepEqual(UI.validateRecord(record(),'env-a','app-a'),record());
  for(const mutate of [r=>r.scope.tenant_id='other',r=>r.proposal.discoveryDigest='d'.repeat(64),
    r=>r.status='APPROVED',r=>r.executionAuthorized=true,r=>r.ownershipAccepted=true,r=>r.approved=true,
    r=>r.revision=Number.MAX_SAFE_INTEGER+1,r=>r.latestGeneration=2,r=>r.sourceSuperseded=true,
    r=>r.proposal.draft.members[0].nativeVm[0]='other',r=>r.proposal.draft.datasetIds.push('orphan'),
    r=>r.proposal.dependencies[1].targetWorkloadId='db',r=>r.proposal.dependencies[1].assertionId='edge-a']) {
    const value=record();mutate(value);assert.throws(()=>UI.validateRecord(value,'env-a','app-a',null,scope));
  }
});
test('metadata editing retains all original source, membership, datasets and unknown evidence',()=>{
  const original=record(),body=UI.editedRequest(original,'New name','new-owner','db\nweb');
  assert.equal(body.expectedRevision,2);assert.equal(body.generation,3);assert.equal(body.resultDigest,original.resultDigest);
  assert.deepEqual(body.dependencies,original.proposal.dependencies);
  for(const field of ['members','datasetIds','consistencyGroups'])assert.deepEqual(body.draft[field],original.proposal.draft[field]);
  assert.equal(body.dependencies[0].observedAt,'2026-09-29T12:00:00.123456+00:00');
  assert.equal(original.proposal.draft.name,'Application A');assert.equal(body.draft.name,'New name');
  body.dependencies.length=0;assert.equal(original.proposal.dependencies.length,2);
});
test('startup and invalid-name changes cannot discard or contradict known dependencies',()=>{
  for(const order of ['web db','db','db db','db foreign'])assert.throws(()=>UI.editedRequest(record(),'Name','owner-a',order));
  for(const name of ['',' Name','Name\n'])assert.throws(()=>UI.editedRequest(record(),name,'owner-a','db web'));
  assert.throws(()=>UI.editedRequest(record(),'Name','owner with spaces','db web'));
  assert.throws(()=>UI.editedRequest({...record(),sourceSuperseded:true},'Name','owner-a','db web'));
});
test('signed-out actions make no API request',async()=>{
  const h=harness(()=>{throw Error('must not run');});h.setAuth({token:null,version:2});
  await h.client.list();await h.client.load();assert.equal(h.calls.length,0);assert.match(h.$('status').textContent,/Sign in/);
});
test('one live list page uses same-origin redirect-rejecting bounded read settings',async()=>{
  const h=harness(()=>response(page()));await h.client.list();assert.equal(h.calls.length,1);
  assert.equal(h.calls[0][0],'/v1/environments/env-a/application-drafts?limit=50');
  const options=h.calls[0][1];assert.equal(options.mode,'same-origin');assert.equal(options.redirect,'error');
  assert.equal(options.cache,'no-store');assert.equal(options.credentials,'omit');assert.equal(options.referrerPolicy,'no-referrer');
  assert.equal(h.$('rows').children.length,1);assert.match(h.$('status').textContent,/live page/);
});
test('list pagination is explicit and encodes cursor once',async()=>{
  let n=0;const item=summary();item.applicationGroupId='app:a';
  const h=harness(()=>response(n++?page([]):page([item],'app:a')));
  await h.client.list();assert.equal(h.calls.length,1);await h.client.list(true);
  assert.match(h.calls[1][0],/&after=app%3Aa$/);assert.equal(h.calls.length,2);assert.equal(h.$('next').hidden,true);
});
test('foreign or malformed list summaries cannot populate the page',async()=>{
  for(const mutate of [p=>p.items[0].scope.tenant_id='other',p=>p.items[0].environmentId='foreign',
    p=>p.items[0].executionAuthorized=true,p=>p.items[0].proposal={},p=>p.nextAfter='other',
    p=>p.items.push(clone(p.items[0])),p=>p.consistency='SNAPSHOT',p=>p.items[0].unknownDependencyCount=3]){
    const value=page();mutate(value);const h=harness(()=>response(value));await h.client.list();
    assert.equal(h.$('rows').children.length,0);assert.match(h.$('status').textContent,/unavailable or inconsistent/);
  }
});
test('empty environment listing keeps unknown generation rather than inventing one',async()=>{
  const p=page([]);p.latestGeneration=null;const h=harness(()=>response(p));await h.client.list();assert.match(h.$('status').textContent,/0 draft/);
});
test('untrusted names are rendered as literal text only',async()=>{
  const p=page();p.items[0].name='<img src=x onerror=alert(1)>';
  const h=harness(()=>response(p));await h.client.list();
  assert.equal(h.$('rows').children[0].children[1].textContent,p.items[0].name);
  assert.equal(h.$('rows').children[0].children[1].innerHTML,undefined);
});
test('current draft opens with retained evidence and explicit confirmation before saving',async()=>{
  const h=harness(()=>response(record()));await h.client.load();assert.equal(h.$('editor').hidden,false);
  assert.equal(h.$('members').children.length,2);assert.equal(h.$('dependencies').children.length,2);
  assert.equal(h.$('save').disabled,true);h.$('name').value='Changed';await h.$('name').fire('input');
  assert.equal(h.$('save').disabled,true);assert.equal(h.$('environment').disabled,true);
  h.$('confirm').checked=true;await h.$('confirm').fire('change');assert.equal(h.$('save').disabled,false);
  h.$('name').value='Changed again';await h.$('name').fire('input');assert.equal(h.$('confirm').checked,false);
});
test('historical and superseded drafts remain read only',async()=>{
  for(const historical of [true,false]){
    const r=record();if(!historical){r.sourceSuperseded=true;r.latestGeneration=4;}
    const h=harness(()=>response(r));if(historical)h.$('revision').value='2';await h.client.load();
    assert.equal(h.$('name').disabled,true);await h.edit();await h.client.save();assert.equal(h.calls.length,1);
  }
});
test('exact save acknowledgement retains assertions and new revision without another GET',async()=>{
  const h=harness((url,options)=>response(options.method==='PUT'?ack(JSON.parse(options.body)):record()));
  await h.client.load();await h.edit();await h.client.save();assert.equal(h.calls.length,2);
  const body=JSON.parse(h.calls[1][1].body);assert.equal(body.expectedRevision,2);assert.equal(body.generation,3);
  assert.equal(body.draft.name,'Edited name');assert.deepEqual(body.dependencies,record().proposal.dependencies);
  assert.match(h.$('binding').textContent,/revision 3/);assert.match(h.$('status').textContent,/Unreviewed draft saved/);
});
test('known startup dependency reversal makes no PUT',async()=>{
  const h=harness(()=>response(record()));await h.client.load();await h.edit();h.$('order').value='web\ndb';
  await h.client.save();assert.equal(h.calls.length,1);assert.match(h.$('status').textContent,/Startup order/);
});
test('form changes while a PUT is in flight cannot alter the frozen request or its validation',async()=>{
  const wait=deferred();const h=harness((url,options)=>options.method==='PUT'?wait.promise:response(record()));
  await h.client.load();await h.edit();const saving=h.client.save();h.$('name').value='Unsent edit';
  wait.resolve(response(ack(JSON.parse(h.calls[1][1].body))));await saving;
  assert.equal(h.$('name').value,'Edited name');assert.match(h.$('status').textContent,/draft saved/);
});
test('changed acknowledgements including dropped unknown edges hold further saves',async()=>{
  for(const mutate of [r=>r.proposal.dependencies.pop(),r=>r.revision=4,r=>r.scope.tenant_id='foreign',
    r=>r.resultDigest='d'.repeat(64),r=>r.proposal.draft.ownerId='substitute',r=>r.ownershipAccepted=true]){
    const h=harness((url,options)=>{if(options.method==='GET')return response(record());const r=ack(JSON.parse(options.body));mutate(r);return response(r);});
    await h.client.load();await h.edit();await h.client.save();assert.match(h.$('status').textContent,/SAVE UNKNOWN/);
    assert.equal(h.$('reconcile').hidden,false);await h.client.save();assert.equal(h.calls.length,2);
  }
});
test('only the exact revision conflict permits a non-unknown refusal',async()=>{
  const h=harness((url,options)=>response(options.method==='PUT'?{error:{code:'APPLICATION_DRAFT_CONFLICT'}}:record(),options.method==='PUT'?409:200));
  await h.client.load();await h.edit();await h.client.save();assert.match(h.$('status').textContent,/Revision\/source conflict/);
  assert.equal(h.$('reconcile').hidden,true);assert.equal(h.$('save').disabled,true);
});
test('non-conflict errors and unexpected status remain unknown without retry',async()=>{
  for(const status of [202,403,404,409,422,503]){
    const h=harness((url,options)=>options.method==='PUT'?response({error:{code:'OTHER'}},status):response(record()));
    await h.client.load();await h.edit();await h.client.save();assert.match(h.$('status').textContent,/SAVE UNKNOWN/);assert.equal(h.calls.length,2);
  }
});
test('lost acknowledgement is reconciled by exact history without another PUT',async()=>{
  let saved;
  const h=harness((url,options)=>{if(options.method==='PUT'){saved=ack(JSON.parse(options.body));throw Error('private token details');}
    return response(url.includes('?revision=3')?{...saved,recordedBy:'another-actor@example.org'}:record());});
  await h.client.load();await h.edit();await h.client.save();await h.client.reconcile();
  assert.equal(h.calls.length,3);assert.equal(h.calls[2][1].method,'GET');assert.match(h.calls[2][0],/\?revision=3$/);
  assert.match(h.$('status').textContent,/not proof this tab committed/);assert.equal(h.$('save').disabled,true);
});
test('missing or changed history does not settle an unknown save',async()=>{
  for(const status of [404,200]){
    const h=harness((url,options)=>{if(options.method==='PUT')throw Error('lost');return response(record(),url.includes('?revision=3')?status:200);});
    await h.client.load();await h.edit();await h.client.save();await h.client.reconcile();
    assert.match(h.$('status').textContent,/remains UNKNOWN/);assert.equal(h.$('reconcile').hidden,false);
  }
});
test('discarding unknown state requires explicit confirmation and never retries',async()=>{
  const h=harness((url,options)=>{if(options.method==='PUT')throw Error('lost');return response(record());});
  await h.client.load();await h.edit();await h.client.save();await h.$('discard').fire('click');
  assert.equal(h.$('reconcile').hidden,false);h.$('confirm-discard').checked=true;await h.$('discard').fire('click');
  assert.equal(h.$('reconcile').hidden,true);assert.equal(h.$('confirm-discard').checked,false);assert.equal(h.calls.length,2);
});
test('clearing identity aborts reads and cannot render late drafts',async()=>{
  const pending=deferred(),h=harness(()=>pending.promise);const loading=h.client.load();const signal=h.calls[0][1].signal;
  h.client.clear();h.setAuth({token:'another',version:2});pending.resolve(response(record()));await loading;
  assert.equal(signal.aborted,true);assert.equal(h.$('editor').hidden,true);assert.equal(h.$('binding').textContent,'');
});
test('late successful PUT after clear cannot display success or repopulate the draft',async()=>{
  const pending=deferred(),h=harness((url,options)=>options.method==='PUT'?pending.promise:response(record()));
  await h.client.load();await h.edit();const saving=h.client.save();const body=JSON.parse(h.calls[1][1].body);
  h.client.clear();h.setAuth({token:'another',version:2});pending.resolve(response(ack(body)));await saving;
  assert.equal(h.$('editor').hidden,true);assert.doesNotMatch(h.$('status').textContent,/saved/);
});
test('revoked identity clears cached data rather than retaining an editable draft',async()=>{
  const h=harness(()=>response({error:{code:'UNAUTHORIZED'}},401));await h.client.load();
  assert.equal(h.rejected(),1);assert.equal(h.$('editor').hidden,true);assert.equal(h.auth().token,null);
});
test('duplicate response JSON cannot lose claims during decoding',async()=>{
  const raw=JSON.stringify(record()).replace('"ownershipAccepted":false','"ownershipAccepted":true,"ownershipAccepted":false');
  const h=harness(()=>new Response(raw,{headers:{'Content-Type':'application/json'}}));await h.client.load();assert.equal(h.$('editor').hidden,true);
});
test('response byte bounds and invalid UTF-8 fail before rendering',async()=>{
  for(const reply of [()=>response(record(),200,{'Content-Length':'9999999'}),
    ()=>new Response(new Uint8Array([0xff]),{headers:{'Content-Type':'application/json'}}),
    ()=>new Response(' '.repeat(524289),{headers:{'Content-Type':'application/json'}})]){
    const h=harness(reply);await h.client.load();assert.equal(h.$('editor').hidden,true);
  }
});
test('read deadline aborts body consumption',async()=>{
  let aborted=false;
  const h=harness((url,options)=>new Response(new ReadableStream({start(stream){
    options.signal.addEventListener('abort',()=>{aborted=true;stream.error(Error('aborted'));});
  }}),{headers:{'Content-Type':'application/json'}}),{timeoutMs:15});
  await h.client.load();assert.equal(aborted,true);assert.equal(h.$('editor').hidden,true);
});
test('navigation warns for unsaved changes and pagehide clears sensitive state',async()=>{
  const h=harness(()=>response(record()));await h.client.load();await h.edit();let prevented=false;
  const event={preventDefault(){prevented=true;}};h.events.beforeunload(event);assert.equal(prevented,true);
  h.events.pagehide();assert.equal(h.$('name').value,'');assert.equal(h.$('binding').textContent,'');
});
test('environment changes invalidate the previous draft before another action',async()=>{
  const h=harness(()=>response(record()));await h.client.load();h.$('environment').value='env-b';await h.$('environment').fire('input');
  assert.equal(h.$('editor').hidden,true);assert.equal(h.$('save').disabled,true);
});

test('the real portal shell clears the composed workspace on sign-out and reauthentication',async()=>{
  const fs=require('node:fs'),vm=require('node:vm'),{webcrypto}=require('node:crypto');
  const elements=new Map(),el=(id)=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
  const origin='https://mobility.example.org',popup={closed:false,close(){this.closed=true;},location:{replace(){}}};
  const context=vm.createContext({document:{getElementById:el,createElement:()=>new Element()},
    window:{location:{origin},addEventListener(){},open:()=>popup},
    Option:function(label,value){return {label,value};},Date,URL,crypto:webcrypto,btoa,
    TextEncoder,TextDecoder,AbortController,Response,setTimeout:()=>1,clearTimeout(){},
    fetch:async(url)=>response(url==='/portal/config.json'?{origin,redirectUri:origin+'/portal/callback',
      issuer:'https://identity.example.org',authorizeUrl:'https://identity.example.org/auth',clientId:'ui',scope:'openid',audience:'api'}:record())});
  const dir=path.resolve(__dirname,'../../../provisioner/controlplane/api/portal');
  vm.runInContext(fs.readFileSync(path.join(dir,'application_drafts.js'),'utf8'),context);
  vm.runInContext(fs.readFileSync(path.join(dir,'app.js'),'utf8'),context);
  await new Promise(setImmediate);
  vm.runInContext('accessToken="synthetic-token"; tokenVersion=1;',context);
  el('draft-environment').value='env-a';el('draft-group').value='app-a';
  await el('draft-load').fire('click');assert.equal(el('draft-editor').hidden,false);
  await el('clear-session').fire('click');assert.equal(el('draft-editor').hidden,true);
  assert.equal(el('draft-name').value,'');assert.equal(el('draft-binding').textContent,'');
  vm.runInContext('accessToken="second-token"; tokenVersion++;',context);
  el('draft-environment').value='env-a';el('draft-group').value='app-a';
  await el('draft-load').fire('click');assert.equal(el('draft-editor').hidden,false);
  await vm.runInContext('signIn()',context);assert.equal(el('draft-editor').hidden,true);
});

test('a rejected response header closes its unread response body',async()=>{
  let cancelled=false;
  const h=harness(()=>new Response(new ReadableStream({cancel(){cancelled=true;}}),
    {headers:{'Content-Type':'text/html'}}));
  await h.client.load();assert.equal(cancelled,true);assert.equal(h.$('editor').hidden,true);
});
