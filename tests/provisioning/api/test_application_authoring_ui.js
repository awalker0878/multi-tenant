'use strict';
const assert = require('node:assert/strict');
const {test} = require('node:test');
const path = require('node:path');
const fs = require('node:fs');
const UI = require(path.resolve(__dirname, '../../../provisioner/controlplane/api/portal/application_drafts.js'));
const copy = (value) => JSON.parse(JSON.stringify(value));
const scope = {organization_id:'org-a',tenant_id:'tenant-a',site_id:'site-a',security_domain_id:'wsd-a',
  endpoint_id:'vcenter-a',native_scope_id:'datacenter-1',platform_family:'vmware'};
const digest = 'a'.repeat(64);
const source = () => ({environmentId:'env-a',generation:3,campaignId:'campaign-a',resultDigest:digest,
  capturedAt:'2026-10-01T12:00:00.123456Z',completeness:'PARTIAL',objectCount:3,collectionErrorCount:1,missingPrivilegeCount:0});
const listing = () => ({format:'hosting-application-draft-list/1',environmentId:'env-a',scope:copy(scope),latestGeneration:3,
  consistency:'LIVE_PAGE',items:[],nextAfter:null,executionAuthorized:false});
const item = (id,kind='vm') => ({resourceKind:kind,nativeId:id,displayName:'Name '+id,unknownCount:1,objectDigest:'b'.repeat(64)});
const page = () => ({environmentId:'env-a',generation:3,items:[item('disk-1','disk'),item('vm-101'),item('vm-102')],nextAfter:null});
function saved(body) {
  return {format:'hosting-application-draft-revision/1',environmentId:'env-a',scope:copy(scope),
    applicationGroupId:body.draft.applicationGroupId,revision:body.expectedRevision+1,generation:body.generation,
    resultDigest:body.resultDigest,proposalDigest:'c'.repeat(64),recordDigest:'d'.repeat(64),
    recordedBy:'recorded-author',recordedAt:'2026-10-01T12:05:00+00:00',
    proposal:{format:'hosting-application-group-candidate/1',discoveryDigest:body.resultDigest,scope:copy(scope),
      draft:copy(body.draft),dependencies:copy(body.dependencies)},status:'UNREVIEWED',latestGeneration:3,
    sourceSuperseded:false,ownershipAccepted:false,executionAuthorized:false};
}
const response = (body,status=200) => new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json'}});
class Element {
  constructor(){this.value='';this.textContent='';this.children=[];this.listeners={};this.checked=false;this.disabled=false;this.hidden=false;}
  replaceChildren(...nodes){this.children=nodes;this.textContent='';}
  append(...nodes){this.children.push(...nodes);}
  addEventListener(event,fn){this.listeners[event]=fn;}
  fire(event){return this.listeners[event]?.({preventDefault(){},target:this});}
}
function harness(handler=null, options={}) {
  const elements=new Map(), calls=[], events={}, selections=[];
  const el=(id)=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
  const $=(id)=>el('draft-'+id);
  let auth={token:'synthetic-token',version:1}, stored;
  const defaultHandler=(url,init)=>{
    if(init.method==='PUT'){stored=saved(JSON.parse(init.body));return response(stored);}
    if(url.endsWith('application-drafts?limit=1'))return response(listing());
    if(url.endsWith('/latest'))return response(source());
    if(url.includes('/objects?'))return response(page());
    return response(stored);
  };
  const client=UI.mount({document:{getElementById:el,createElement:()=>new Element()},window:{addEventListener:(n,fn)=>{events[n]=fn;}},
    session:()=>auth,fetch:async(url,init)=>{calls.push([url,init]);return handler?handler(url,init,defaultHandler):defaultHandler(url,init);},
    rejectSession:()=>{auth={token:null,version:auth.version+1};client.clear();},
    onSelection:(record)=>selections.push(record),...options});
  $('environment').value='env-a';$('group').value='application-a';
  async function select(nativeId,id) {
    const row=$('observations').children.find((row)=>row.children[0].textContent===nativeId);
    assert.ok(row,'observed VM exists');
    const input=row.children[3].children[0].children[0];input.value=id;await input.fire('input');
    await row.children[4].children[0].fire('click');
  }
  function group(id='data-group',ids='database-data\nweb-data') {
    $('data-group').value=id;$('data-ids').value=ids;client.addGroup();
  }
  function edge(unknown=false) {
    const fields={'edge-id':unknown?'edge-b':'edge-a','edge-from':'web','edge-to':unknown?'':'db',
      'edge-relation':unknown?'SERVICE_CALL':'STARTS_AFTER','edge-state':unknown?'UNKNOWN':'KNOWN',
      'edge-reason':unknown?'EXTERNAL_DEPENDENCY':'','edge-source':unknown?'MONITORING':'CMDB',
      'edge-reference':unknown?'trace-a':'cmdb-ticket-a','edge-time':'2026-10-01T12:00:00.123456Z'};
    for(const [key,value] of Object.entries(fields))$(key).value=value;
    client.addEdge();
  }
  async function prepare() {
    await client.start();await client.objects();await select('vm-101','db');await select('vm-102','web');group();
    $('name').value='Application A';$('owner').value='owner-a';await $('name').fire('input');
  }
  function confirm(){ $('confirm').checked=true;$('confirm').fire('change'); }
  return {client,$,el,calls,events,selections,select,group,edge,prepare,confirm,setAuth:(value)=>{auth=value;}};
}
function deferred(){let resolve;const promise=new Promise((r)=>{resolve=r;});return {resolve,promise};}

test('initial draft uses existing exact-scope reads then one revision-zero PUT and no mutation API',async()=>{
  const h=harness();await h.prepare();h.edge();h.edge(true);h.confirm();
  assert.equal(h.client.selection(),null);await h.client.save();
  assert.equal(h.calls.length,4);assert.match(h.calls[0][0],/application-drafts\?limit=1$/);
  assert.match(h.calls[1][0],/generations\/latest$/);assert.match(h.calls[2][0],/generations\/3\/objects\?limit=50$/);
  const body=JSON.parse(h.calls[3][1].body);assert.equal(body.expectedRevision,0);assert.equal(body.resultDigest,digest);
  assert.deepEqual(body.draft.members.map((m)=>m.nativeVm[4]),['vm-101','vm-102']);
  assert.deepEqual(body.draft.startupOrder,['db','web']);assert.equal(body.dependencies[1].targetWorkloadId,null);
  assert.equal(body.dependencies[0].observedAt,'2026-10-01T12:00:00.123456+00:00');
  assert.equal(h.client.selection().revision,1);assert.equal(h.client.selection().executionAuthorized,false);
  assert.equal(h.$('authoring').hidden,true);assert.equal(h.$('members').children[0].children[2].textContent,'Read only');
});
test('unsigned source summaries do not become native or owner qualification',async()=>{
  for(const completeness of ['PARTIAL','UNKNOWN','COMPLETE']){
    const h=harness((url,init,fallback)=>{const value=source();value.completeness=completeness;
      if(completeness==='COMPLETE')value.collectionErrorCount=0;
      return url.endsWith('/latest')?response(value):fallback(url,init);});
    await h.prepare();h.confirm();await h.client.save();
    assert.equal(h.client.selection().ownershipAccepted,false);
    assert.equal(h.client.selection().status,'UNREVIEWED');
    assert.deepEqual(h.client.selection().proposal.dependencies,[]);
  }
});
test('signed-out creation and historical IDs do not make source requests',async()=>{
  const h=harness();h.setAuth({token:null,version:2});await h.client.start();assert.equal(h.calls.length,0);
  h.setAuth({token:'new',version:3});h.$('revision').value='1';await h.client.start();assert.equal(h.calls.length,0);
});
test('scope discovery must be a valid authorized listing not an arbitrary scope object',async()=>{
  for(const mutate of [p=>p.environmentId='other',p=>p.scope.platform_family='other',p=>p.executionAuthorized=true,
    p=>p.latestGeneration=null,p=>p.latestGeneration=9007199254740992,p=>p.scope.organization_id='',p=>p.extra=true]){
    const value=listing();mutate(value);const h=harness(()=>response(value));await h.client.start();
    assert.equal(h.calls.length,1);assert.equal(h.$('editor').hidden,true);
  }
});
test('initial observation must match the just-read generation with explicit typed coverage',async()=>{
  for(const mutate of [p=>p.generation=4,p=>p.environmentId='other',p=>p.resultDigest='invalid',p=>p.objectCount=true,
    p=>p.capturedAt='2026-02-30T12:00:00Z',p=>p.completeness='ELIGIBLE',p=>p.completeness='COMPLETE',p=>p.authorized=true]){
    const value=source();mutate(value);
    const h=harness((url,init,fallback)=>url.endsWith('/latest')?response(value):fallback(url,init));
    await h.client.start();assert.equal(h.calls.length,2);assert.equal(h.$('editor').hidden,true);assert.equal(h.client.selection(),null);
  }
});
test('creation inputs cannot silently switch environment or reload an unrelated draft',async()=>{
  const h=harness();await h.client.start();h.$('environment').value='other';await h.$('environment').fire('input');
  await h.client.list();await h.client.load();await h.client.start();assert.equal(h.calls.length,2);
  await h.client.objects();assert.match(h.calls[2][0],/environments\/env-a\//);
});
test('late scope and observation responses cannot reopen a cleared tab',async()=>{
  for(const delayedPath of ['application-drafts?limit=1','/latest']){
    const wait=deferred();const h=harness((url,init,fallback)=>url.endsWith(delayedPath)?wait.promise:fallback(url,init));
    const pending=h.client.start();await new Promise(setImmediate);h.client.clear();
    wait.resolve(response(delayedPath==='/latest'?source():listing()));await pending;
    assert.equal(h.$('editor').hidden,true);assert.equal(h.$('authoring').hidden,true);assert.equal(h.client.selection(),null);
  }
});
test('identity rejection during source reads clears sensitive creation state',async()=>{
  const h=harness((url,init,fallback)=>url.endsWith('/latest')?response({error:'unauthorized'},401):fallback(url,init));
  await h.client.start();assert.equal(h.$('environment').value,'');assert.equal(h.$('editor').hidden,true);
});
test('only observed VMs can be selected; aliases must be explicit and unique',async()=>{
  const h=harness();await h.client.start();await h.client.objects();assert.equal(h.$('observations').children.length,2);
  await h.select('vm-101','db');await h.select('vm-102','db');assert.equal(h.$('members').children.length,1);
  await h.select('vm-102','bad logical id');assert.equal(h.$('members').children.length,1);
  await h.select('vm-102','web');assert.equal(h.$('members').children.length,2);
  assert.equal(h.$('observations').children[0].children[3].textContent,'Selected');
});
test('pending member aliases survive group rendering and prevent an incomplete save',async()=>{
  const h=harness();await h.prepare();
  // Remove a member explicitly, then type but do not add its replacement.
  await h.$('members').children[1].children[2].children[0].fire('click');
  const row=h.$('observations').children[1];row.children[3].children[0].children[0].value='web-new';
  h.group('other-data','another-dataset');
  assert.equal(h.$('observations').children[1].children[3].children[0].children[0].value,'web-new');
  h.confirm();await h.client.save();assert.equal(h.calls.length,3);assert.match(h.$('status').textContent,/unfinished/);
});
test('a terminal identity page cannot trigger another enumeration request',async()=>{
  const h=harness();await h.client.start();await h.client.objects();
  assert.equal(h.$('objects').disabled,true);
  const count=h.calls.length;await h.client.objects();assert.equal(h.calls.length,count);
});
test('dataset groups reject duplicates and orphan-like reuse instead of silently repartitioning',async()=>{
  const h=harness();await h.prepare();h.group('other','database-data');assert.equal(h.$('datasets').children.length,1);
  h.group('data-group','other-data');assert.equal(h.$('datasets').children.length,1);
  h.group('other','duplicate duplicate');assert.equal(h.$('datasets').children.length,1);
  h.group('other','');assert.equal(h.$('datasets').children.length,1);
  h.group('other','x'.repeat(129001));assert.equal(h.$('datasets').children.length,1);
});
test('known dependencies require selected targets; unknown edges preserve explicit reasons',async()=>{
  const h=harness();await h.prepare();h.edge(true);
  assert.equal(h.$('dependencies').children[0].children[4].textContent,'UNKNOWN');
  assert.equal(h.$('dependencies').children[0].children[5].textContent,'EXTERNAL_DEPENDENCY');
  h.edge();assert.equal(h.$('dependencies').children.length,2);
  h.edge();assert.equal(h.$('dependencies').children.length,2); // duplicate ID refused
});
test('removing a referenced member requires explicit removal of its assertions',async()=>{
  const h=harness();await h.prepare();h.edge();
  await h.$('members').children[0].children[2].children[0].fire('click');
  assert.equal(h.$('members').children.length,2);assert.match(h.$('status').textContent,/assertions explicitly/);
  await h.$('dependencies').children[0].children[9].children[0].fire('click');
  await h.$('members').children[0].children[2].children[0].fire('click');assert.equal(h.$('members').children.length,1);
});
test('dependency addition never invents source provenance, target, or timestamp',async()=>{
  for(const [field,value] of [['edge-time',''],['edge-time','2026-10-01T12:00:00'],['edge-source',''],
    ['edge-reference',''],['edge-to','foreign'],['edge-reason','NOT_OBSERVED'],['edge-from','foreign']]){
    const h=harness();await h.prepare();h.edge();
    // Removing the added edge keeps fields clear; populate once with an invalid value.
    await h.$('dependencies').children[0].children[9].children[0].fire('click');
    const fields={'edge-id':'edge-x','edge-from':'web','edge-to':'db','edge-relation':'STARTS_AFTER','edge-state':'KNOWN',
      'edge-reason':'','edge-source':'CMDB','edge-reference':'ticket','edge-time':'2026-10-01T12:00:00Z'};
    for(const [id,v] of Object.entries(fields))h.$(id).value=v;h.$(field).value=value;h.client.addEdge();
    assert.equal(h.$('dependencies').children.length,0);
  }
});
test('startup contradictions and pending assertion fields block PUT before network use',async()=>{
  const h=harness();await h.prepare();h.edge();h.$('order').value='web db';h.confirm();await h.client.save();
  assert.equal(h.calls.length,3);assert.match(h.$('status').textContent,/Startup order/);
  h.$('order').value='db web';h.$('edge-id').value='not-added';h.confirm();await h.client.save();
  assert.equal(h.calls.length,3);assert.match(h.$('status').textContent,/unfinished/);
});
test('creation is not comparison input and every local change resets save confirmation',async()=>{
  const h=harness();await h.prepare();h.confirm();assert.equal(h.$('confirm').checked,true);
  h.$('edge-id').value='edge';await h.$('edge-id').fire('input');assert.equal(h.$('confirm').checked,false);
  assert.equal(h.client.selection(),null);assert.ok(h.selections.every((value)=>value===null));
});
test('lost first-save acknowledgement reconciles exact revision one without retrying PUT',async()=>{
  let stored;const h=harness((url,init,fallback)=>{
    if(init.method==='PUT'){stored=saved(JSON.parse(init.body));throw new Error('sensitive transport details');}
    return url.endsWith('?revision=1')?response(stored):fallback(url,init);});
  await h.prepare();h.confirm();await h.client.save();assert.match(h.$('status').textContent,/SAVE UNKNOWN/);
  await h.client.save();await h.client.start();await h.client.objects();assert.equal(h.calls.length,4);
  await h.client.reconcile();assert.equal(h.calls.length,5);assert.match(h.calls[4][0],/\?revision=1$/);
  assert.equal(h.client.selection(),null);assert.equal(h.$('authoring').hidden,true);
});
test('changed initial acknowledgements remain unknown and never become a saved selection',async()=>{
  for(const mutate of [r=>r.revision=2,r=>r.scope.tenant_id='foreign',r=>r.resultDigest='e'.repeat(64),
    r=>r.proposal.draft.members.pop(),r=>r.proposal.draft.datasetIds.push('foreign'),r=>r.executionAuthorized=true]){
    const h=harness((url,init,fallback)=>{if(init.method!=='PUT')return fallback(url,init);
      const value=saved(JSON.parse(init.body));mutate(value);return response(value);});
    await h.prepare();h.confirm();await h.client.save();assert.match(h.$('status').textContent,/SAVE UNKNOWN/);
    assert.equal(h.client.selection(),null);assert.equal(h.$('add-group').disabled,true);
  }
});
test('a first-save revision/source conflict never overwrites or automatically loads the existing draft',async()=>{
  const h=harness((url,init,fallback)=>init.method==='PUT'?response({error:{code:'APPLICATION_DRAFT_CONFLICT'}},409):fallback(url,init));
  await h.prepare();h.confirm();await h.client.save();assert.equal(h.calls.length,4);
  assert.equal(h.$('editor').hidden,true);assert.equal(h.$('authoring').hidden,true);assert.equal(h.$('save').disabled,true);
});
test('missing revision-one history leaves creation save unresolved',async()=>{
  const h=harness((url,init,fallback)=>{if(init.method==='PUT')throw Error('lost');
    return url.endsWith('?revision=1')?response({error:'absent'},404):fallback(url,init);});
  await h.prepare();h.confirm();await h.client.save();await h.client.reconcile();
  assert.match(h.$('status').textContent,/remains UNKNOWN/);assert.equal(h.$('reconcile').hidden,false);
});
test('clearing or changing identity during the first PUT discards late acknowledgement',async()=>{
  const wait=deferred();const h=harness((url,init,fallback)=>init.method==='PUT'?wait.promise:fallback(url,init));
  await h.prepare();h.confirm();const pending=h.client.save();const body=JSON.parse(h.calls.at(-1)[1].body);
  h.setAuth({token:'different',version:2});h.client.clear();wait.resolve(response(saved(body)));await pending;
  assert.equal(h.$('editor').hidden,true);assert.equal(h.client.selection(),null);assert.equal(h.$('owner').value,'');
});
test('pagehide clears all creation data and local edits warn before navigation',async()=>{
  const h=harness();await h.prepare();h.edge(true);let warned=false;
  h.events.beforeunload({preventDefault(){warned=true;}});assert.equal(warned,true);
  h.events.pagehide();for(const id of ['observations','members','datasets','dependencies'])assert.equal(h.$(id).children.length,0);
  assert.equal(h.$('authoring').hidden,true);assert.equal(h.$('binding').textContent,'');
});
test('cursor is the exact last identity encoding and never a supplied URL',()=>{
  const rows=Array.from({length:50},(_,i)=>item('vm-'+i));rows[49]=item('vm-\u{1f680}');
  const next=UI.objectCursor(rows[49]), value={environmentId:'env-a',generation:3,items:rows,nextAfter:next};
  assert.equal(UI.validateObjectPage(value,{...source(),objectCount:51},new Set(),null,0).nextAfter,next);
  for(const cursor of ['https://evil.invalid',next+'=',UI.objectCursor(rows[0]),'']){
    assert.throws(()=>UI.validateObjectPage({...value,nextAfter:cursor},{...source(),objectCount:51},new Set(),null,0));
  }
});
test('invalid pages fail before any rows are retained or PUT allowed',async()=>{
  for(const mutate of [p=>p.environmentId='foreign',p=>p.generation=4,p=>p.nextAfter='invalid',
    p=>p.items[1].resourceKind='owner-approved',p=>p.items[1].objectDigest='bad',p=>p.items[1].unknownCount=-1,
    p=>p.items[1].nativeId='bad\n',p=>p.items[1].executionAuthorized=true,p=>p.items.push(copy(p.items[1])),p=>p.items.pop()]){
    const value=page();mutate(value);const h=harness((url,init,fallback)=>url.includes('/objects?')?response(value):fallback(url,init));
    await h.client.start();await h.client.objects();assert.equal(h.$('observations').children.length,0);
    assert.equal(h.$('save').disabled,true);assert.equal(h.$('objects').disabled,true);
  }
});
test('explicit pagination retains selected members and rejects cross-page repetitions',async()=>{
  const rows=Array.from({length:50},(_,i)=>item('vm-'+String(i).padStart(3,'0'))), next=UI.objectCursor(rows.at(-1));
  for(const repeated of [false,true]){
    const h=harness((url,init,fallback)=>{
      if(url.endsWith('/latest'))return response({...source(),objectCount:52});
      if(url.includes('/objects?'))return response({environmentId:'env-a',generation:3,
        items:url.includes('&after=')?[item(repeated?'vm-000':'vm-050'),item('vm-051')]:rows,nextAfter:url.includes('&after=')?null:next});
      return fallback(url,init);});
    await h.client.start();assert.equal(h.calls.length,2);await h.client.objects();assert.equal(h.calls.length,3);
    await h.select('vm-000','db');await h.select('vm-001','web');await h.client.objects();
    assert.equal(h.calls.length,4);assert.match(h.calls[3][0],new RegExp('&after='+next+'$'));
    assert.equal(h.$('members').children.length,2);
    if(repeated)assert.match(h.$('status').textContent,/inconsistent/);else assert.match(h.$('observation-status').textContent,/chain ended/);
  }
});
test('timestamps reject calendar normalization or hidden local-zone conversion and preserve microseconds',()=>{
  assert.equal(UI.utcInput('2026-10-01T12:00:00.1Z'),'2026-10-01T12:00:00.100000+00:00');
  assert.equal(UI.utcInput('2026-10-01T12:00:00.000000Z'),'2026-10-01T12:00:00+00:00');
  assert.equal(UI.utcInput('2026-10-01T12:00:00.123456Z'),'2026-10-01T12:00:00.123456+00:00');
  for(const v of ['2026-02-30T12:00:00Z','2026-10-01T24:00:00Z','2026-10-01T12:00:60Z',
    '2026-10-01T12:00:00-04:00','2026-10-01T12:00:00.1234567Z','0000-01-01T00:00:00Z','2026-10-01T12:00:00'])assert.throws(()=>UI.utcInput(v));
});
test('source labels and native names are literal text, never markup',async()=>{
  const value=page();value.items[1].displayName='<img src=x onerror=alert(1)>';
  const h=harness((url,init,fallback)=>url.includes('/objects?')?response(value):fallback(url,init));
  await h.client.start();await h.client.objects();assert.equal(h.$('observations').children[0].children[1].textContent,value.items[1].displayName);
  assert.equal(h.$('observations').children[0].children[1].innerHTML,undefined);
});
test('framing mismatches do not leave a usable initial source',async()=>{
  const h=harness(()=>new Response(JSON.stringify(listing()),{headers:{'Content-Type':'application/json','Content-Length':'1'}}));
  await h.client.start();assert.equal(h.$('editor').hidden,true);assert.equal(h.calls.length,1);
});
test('decoded Fetch bytes are bounded without comparing to compressed wire length',async()=>{
  const h=harness((url,init,fallback)=>url.endsWith('application-drafts?limit=1')?
    new Response(JSON.stringify(listing()),{headers:{'Content-Type':'application/json',
      'Content-Encoding':'gzip','Content-Length':'40'}}):fallback(url,init));
  await h.client.start();assert.equal(h.$('editor').hidden,false);assert.equal(h.calls.length,2);
});
test('native scope is a bounded native selector, not a truncated logical ID',()=>{
  const value=listing();value.scope.native_scope_id='folder/with spaces/'+'x'.repeat(200);
  assert.deepEqual(UI.validateList(value,'env-a').scope,value.scope);
  for(const v of ['','bad\n','x'.repeat(513)])assert.throws(()=>UI.validateList({...value,scope:{...value.scope,native_scope_id:v}},'env-a'));
});

// Python supplies real API/domain serialization for an additional cross-language contract case.
if(process.env.HOSTING_AUTHORING_FIXTURE){
  test('actual Python API summaries and proposal parser agree with the browser-created request',()=>{
    const f=JSON.parse(fs.readFileSync(process.env.HOSTING_AUTHORING_FIXTURE,'utf8'));
    const list=UI.validateList(f.listing,f.source.environmentId,null,null,1);
    const src={...UI.validateGeneration(f.source,list.environmentId,list.latestGeneration),scope:list.scope};
    UI.validateObjectPage(f.page,src,new Set(),null,0);
    const body=UI.creationRequest(src,f.content.draft.applicationGroupId,f.content.draft.name,f.content.draft.ownerId,
      f.content.draft.members,f.content.draft.consistencyGroups,f.content.dependencies,f.content.draft.startupOrder.join('\n'));
    assert.deepEqual(UI.validateRecord(f.saved,src.environmentId,body.draft.applicationGroupId,1,src.scope).proposal.draft,body.draft);
    fs.writeFileSync(process.env.HOSTING_AUTHORING_REQUEST,JSON.stringify(body));
  });
}

test('native identity paging refuses to discard pending aliases on a nonterminal page',async()=>{
  const rows=Array.from({length:50},(_,i)=>item('vm-'+String(i).padStart(3,'0')));
  const h=harness((url,init,fallback)=>url.endsWith('/latest')?response({...source(),objectCount:51}):
    url.includes('/objects?')?response({environmentId:'env-a',generation:3,items:rows,nextAfter:UI.objectCursor(rows.at(-1))}):fallback(url,init));
  await h.client.start();await h.client.objects();assert.equal(h.$('objects').disabled,false);
  h.$('observations').children[0].children[3].children[0].children[0].value='unadded';
  await h.client.objects();assert.equal(h.calls.length,3);assert.match(h.$('status').textContent,/unfinished member/);
  assert.equal(h.$('observations').children[0].children[3].children[0].children[0].value,'unadded');
});
test('initial proposal enforces member, dataset, group, dependency and byte budgets',async()=>{
  const h=harness();await h.prepare();h.confirm();await h.client.save();
  const body=JSON.parse(h.calls.at(-1)[1].body), draft=body.draft, src={...source(),scope};
  const make=(members=draft.members,groups=draft.consistencyGroups,edges=[],order=members.map(m=>m.workloadId).join(' '))=>
    UI.creationRequest(src,'application-a','Application A','owner-a',members,groups,edges,order);
  assert.throws(()=>make(Array.from({length:101},(_,i)=>({workloadId:'member-'+i,nativeVm:[...draft.members[0].nativeVm.slice(0,4),'vm-'+i]}))));
  assert.throws(()=>make(draft.members,[{groupId:'g',datasetIds:Array.from({length:1001},(_,i)=>'dataset-'+i)}]));
  assert.throws(()=>make(draft.members,Array.from({length:101},(_,i)=>({groupId:'g-'+i,datasetIds:['dataset-'+i]}))));
  const edge={assertionId:'edge',sourceWorkloadId:'web',targetWorkloadId:null,relation:'SERVICE_CALL',state:'UNKNOWN',
    unknownReason:'NOT_OBSERVED',source:'CMDB',sourceReference:'ticket',observedAt:'2026-10-01T12:00:00+00:00'};
  assert.throws(()=>make(draft.members,draft.consistencyGroups,Array.from({length:501},(_,i)=>({...edge,assertionId:'edge-'+i}))));
  // All field/count bounds are individually valid; the combined serialized request is not.
  const many=Array.from({length:500},(_,i)=>({...edge,assertionId:'edge-'+i,sourceReference:'x'.repeat(128)}));
  assert.throws(()=>make(draft.members,draft.consistencyGroups,many),/request limit/);
});
test('page budget stops explicit enumeration without claiming whole-estate completeness',async()=>{
  let n=0;
  const h=harness((url,init,fallback)=>{
    if(url.endsWith('/latest'))return response({...source(),objectCount:10050});
    if(url.includes('/objects?')){
      const rows=Array.from({length:50},()=>item('vm-'+String(n++).padStart(5,'0')));
      return response({environmentId:'env-a',generation:3,items:rows,nextAfter:UI.objectCursor(rows.at(-1))});
    }
    return fallback(url,init);
  });
  await h.client.start();for(let i=0;i<200;i++)await h.client.objects();
  assert.equal(h.calls.length,202);assert.equal(h.$('objects').disabled,true);
  await h.client.objects();assert.equal(h.calls.length,202);assert.match(h.$('observation-status').textContent,/budget/i);
  assert.equal(h.client.selection(),null);
});
test('an in-flight initial PUT is frozen despite later local field changes',async()=>{
  const wait=deferred();const h=harness((url,init,fallback)=>init.method==='PUT'?wait.promise:fallback(url,init));
  await h.prepare();h.confirm();const operation=h.client.save();await new Promise(setImmediate);
  const body=JSON.parse(h.calls.at(-1)[1].body);
  h.$('name').value='changed';h.$('data-group').value='changed';h.client.addGroup();
  await h.client.start();await h.client.objects();await h.client.save();assert.equal(h.calls.length,4);
  wait.resolve(response(saved(body)));await operation;
  assert.equal(h.client.selection().proposal.draft.name,'Application A');assert.equal(h.$('name').value,'Application A');
});


test('digest fields never accept array-to-string coercion',async()=>{
  for(const phase of ['source','page','save']){
    const h=harness((url,init,fallback)=>{
      if(phase==='source' && url.endsWith('/latest'))return response({...source(),resultDigest:[digest]});
      if(phase==='page' && url.includes('/objects?')){const value=page();value.items[0].objectDigest=['b'.repeat(64)];return response(value);}
      if(phase==='save' && init.method==='PUT'){const value=saved(JSON.parse(init.body));value.recordDigest=[value.recordDigest];return response(value);}
      return fallback(url,init);
    });
    if(phase==='save'){await h.prepare();h.confirm();await h.client.save();assert.match(h.$('status').textContent,/SAVE UNKNOWN/);}
    else{await h.client.start();if(phase==='page')await h.client.objects();assert.equal(h.$('save').disabled,true);}
    assert.equal(h.client.selection(),null);
  }
});
