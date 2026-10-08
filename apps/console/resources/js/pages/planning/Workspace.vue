<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue';
import { Link, useForm } from '@inertiajs/vue3';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';
import type { Candidate, Endpoint, PlanningRecord } from '../../features/planning/contracts';
import { usePlanningAccess } from '../../features/planning/useAccess';
const props=defineProps<{tenantId:string;applicationId:string;environment:string;revisionId:string;record:PlanningRecord|null;sites:string[];notice:string|null;comparison?:{changes:{path:string;change:string}[];approval_reusable:boolean}|null}>();
const base=`/tenants/${props.tenantId}/applications/${props.applicationId}/environments/${props.environment}/planning`;
const query=`?sites=${props.sites.join(',')}`;
const kind=props.record?.binding?'plans':'assessments';
const {validity,now,unavailable}=usePlanningAccess(props.record?`${base}/${kind}/${props.record.id}/status${query}`:null,props.record?.validity);
const rows=ref([{site:'',endpoint:'',endpoints:[] as Endpoint[]},{site:'',endpoint:'',endpoints:[] as Endpoint[]}]);
const destinationRequests = new Map<number, AbortController>();
function resetDestination(index: number) {
  destinationRequests.get(index)?.abort();
  destinationRequests.delete(index);
  rows.value[index].endpoints = []; rows.value[index].endpoint = '';
}
onUnmounted(() => { for (const request of destinationRequests.values()) request.abort(); });
const selectionError=ref('');
const action=ref('application.provision');const method=ref('native_api');const executor=ref('');const lane=ref('operational');const compare=ref('');
type CommandBody = {revision_id?:string;action?:string;method?:string;candidates?:{site_id:string;endpoint_id:string;generation_id:string}[];assessment_id?:string;candidate?:number;request?:{action:string;method:string;lane:string;executor_ids:string[];valid_until:number};plan_id?:string;plan_digest?:string;other_plan_id?:string};
const command=useForm({operation:'assessments',command_key:crypto.randomUUID() as string,sites:[] as string[],body:{} as CommandBody});
const errorMessage=ref('');
const uncertain=ref(false);
const blocked=computed(()=>command.processing || unavailable.value || uncertain.value);
const canApprove=computed(()=>props.record?.content?.execution_ready && validity.value?.current && props.record.content.valid_until>now.value && props.record.content.input_fresh_until>now.value && !blocked.value);
async function load(index:number) {
  selectionError.value='';
  resetDestination(index);
  const row=rows.value[index], site=row.site, controller=new AbortController();
  destinationRequests.set(index, controller);
  const deadline=setTimeout(()=>controller.abort(),12000);
  try {
    const response=await fetch(`${base}/destinations/${site}`,{headers:{Accept:'application/json'},cache:'no-store',redirect:'manual',signal:controller.signal});
    if(!response.ok || !response.headers.get('Content-Type')?.includes('application/json'))throw new Error();
    const result=await response.json() as {items:Endpoint[]};
    if(!controller.signal.aborted && row.site===site && destinationRequests.get(index)===controller)row.endpoints=result.items;
  }catch{if(destinationRequests.get(index)===controller)selectionError.value='This site is unavailable or outside your current access.';}
  finally{clearTimeout(deadline);if(destinationRequests.get(index)===controller)destinationRequests.delete(index);}
}
function send(operation:string, body:CommandBody, sites:string[]) {
  if(blocked.value)return;
  command.operation=operation;command.body=body;command.sites=sites;command.command_key=crypto.randomUUID();submit();
}
function submit(){command.post(`${base}/commands`,{preserveState:'errors',onError:errors=>{uncertain.value=errors.planning_status==='503';errorMessage.value=errors.command??'This command is held.';},onSuccess:()=>{uncertain.value=false;}});}
function assess(){
  const candidates:Candidate[]=[];
  for(const row of rows.value){const endpoint=row.endpoints.find(e=>e.endpoint_id===row.endpoint);if(endpoint?.generation_id)candidates.push({site_id:row.site,endpoint_id:endpoint.endpoint_id,generation_id:endpoint.generation_id});}
  if(!candidates.length){selectionError.value='Select a collected destination.';return;}
  send('assessments',{revision_id:props.revisionId,action:action.value,method:method.value,candidates:candidates.map(c=>({...c}))},candidates.map(c=>c.site_id));
}
function compile(index:number){if(!props.record)return;send('plans',{assessment_id:props.record.id,candidate:index,request:{action:props.record.action??'',method:props.record.method??'',lane:lane.value,executor_ids:executor.value.split(',').map(v=>v.trim()),valid_until:Math.floor(Date.now()/1000)+900}},props.sites);}
</script>
<template>
<CatalogueLayout title="Destination assessment and plan review" :tenant-id="tenantId">
  <p class="max-w-3xl text-slate-700">Review this application revision against exact destinations. Findings explain the evidence and remaining work. A plan does not reserve capacity or authorize execution.</p>
  <p class="my-3 break-all text-xs">Intent revision {{revisionId}}</p>
  <p v-if="notice" role="status" class="my-4 rounded border border-teal-700 p-4">{{notice}}</p>
  <p v-if="unavailable" role="alert">Current authority is unavailable. Commands are paused until it can be checked.</p>
  <p v-if="errorMessage" role="alert" class="my-4 text-red-800">{{errorMessage}}</p>
  <button v-if="uncertain" :disabled="command.processing" @click="submit">Retry the unchanged command</button>
  <form v-if="!record" class="mt-7 space-y-5" @submit.prevent="assess">
    <fieldset :disabled="blocked"><legend class="text-xl font-semibold">Compare collected destinations</legend>
      <div class="grid gap-5 md:grid-cols-2"><section v-for="(row,index) in rows" :key="index" class="mt-4 rounded-xl border border-slate-300 p-5">
        <h2 class="font-semibold">Destination {{index+1}}{{index===1?' (optional)':''}}</h2>
        <label :for="`site-${index}`">Approved site ID<input :id="`site-${index}`" v-model="row.site" maxlength="36" :required="index===0" @input="resetDestination(index)" /></label>
        <button type="button" class="secondary" @click="load(index)">Load collected endpoints</button>
        <label :for="`endpoint-${index}`">Endpoint<select :id="`endpoint-${index}`" v-model="row.endpoint" :required="index===0"><option value="">Choose a collected endpoint</option><option v-for="e in row.endpoints" :key="e.endpoint_id" :value="e.endpoint_id" :disabled="!e.generation_id">{{e.label}} · {{e.platform}} · {{e.reason??'current collection'}}</option></select></label>
      </section></div>
      <div class="grid max-w-3xl gap-4 sm:grid-cols-2"><label for="planning-action">Action<select id="planning-action" v-model="action"><option value="application.provision">Provision</option><option value="application.migrate">Migrate</option><option value="application.recover">Recover</option><option value="application.retire">Retire</option></select></label><label for="planning-method">Method<select id="planning-method" v-model="method"><option value="native_api">Native API provisioning</option><option value="native_api_export_import">Native VM export and import</option><option value="forward_recovery">Forward recovery</option><option value="owned_retirement">Owned resource retirement</option></select></label></div>
      <p v-if="selectionError" role="alert">{{selectionError}}</p><button type="submit">Assess destinations</button>
    </fieldset>
  </form>
  <section v-if="record?.results" class="mt-6 space-y-5">
    <h2 class="text-xl font-semibold">Requirement comparison</h2>
    <div class="grid gap-5 lg:grid-cols-2"><article v-for="(result,index) in record.results" :key="result.endpoint_id" class="min-w-0 rounded-xl border border-slate-300 p-5">
      <h3 class="text-lg font-semibold">{{result.platform}} · {{result.status}}</h3><p class="break-all text-xs">Site {{result.site_id}} · generation {{result.generation_id}}</p><p>Capacity is unreserved.</p>
      <ul class="mt-4 space-y-3"><li v-for="(finding,i) in result.findings" :key="i" class="rounded border border-slate-200 p-3"><strong>{{finding.requirement}} · {{finding.status}}</strong><p>{{finding.mandatory?'Required':'Preferred'}} · {{finding.reason.replaceAll('_',' ')}}</p><p class="text-sm">{{finding.remediation}}</p><p class="break-all text-xs text-slate-600">Source: {{finding.source}}</p></li></ul>
      <button :disabled="blocked || !executor" @click="compile(index)">Compile review proposal for this destination</button>
    </article></div>
    <fieldset :disabled="blocked" class="max-w-2xl"><legend class="font-semibold">Bind the proposal</legend><label for="plan-executors">Intended executor IDs (comma separated)<input id="plan-executors" v-model="executor" required maxlength="1200" /></label><label for="plan-lane">Authority lane<select id="plan-lane" v-model="lane"><option value="operational">Operational</option><option value="isolated_campaign">Isolated campaign</option></select></label><p>Proposals expire after 15 minutes. Missing evidence remains a hold in either lane; campaign authority is separately bounded.</p></fieldset>
  </section>
  <section v-if="record?.content && record.binding" class="mt-6 space-y-5">
    <h2 class="text-xl font-semibold">Immutable plan review</h2><p>{{record.content.action}} · {{record.content.lane}}</p>
    <dl class="space-y-2 text-sm"><dt>Content digest</dt><dd class="break-all">{{record.binding.content_digest}}</dd><dt>Approval binding</dt><dd class="break-all">{{record.binding.digest}}</dd><dt>Valid until</dt><dd>{{new Date(record.content.valid_until*1000).toLocaleString()}}</dd></dl>
    <div role="status" class="rounded-xl border border-amber-500 p-5"><h3 class="font-semibold">{{canApprove?'Ready for approval handoff':'Review held'}}</h3><ul><li v-for="hold in validity?.holds ?? record.content.holds" :key="hold">{{hold.replaceAll('_',' ')}}</li><li v-if="record.content.valid_until<=now || record.content.input_fresh_until<=now">Plan or facts expired. Reassess and review a new proposal.</li></ul></div>
    <p>Downtime assumption: {{record.content.budgets.downtime_seconds}} seconds; application acceptance is still required.</p>
    <h3 class="text-lg font-semibold">Effects and recovery boundaries</h3><ol class="space-y-3"><li v-for="effect in record.content.effects" :key="effect.id" class="rounded border border-slate-300 p-4"><strong>{{effect.id.replaceAll('_',' ')}}</strong><span v-if="effect.destructive" class="ml-2 font-semibold text-red-800">Changes or removes state</span><p>After: {{effect.after.join(', ')||'start'}} · {{effect.boundary.replaceAll('_',' ')}}</p><p>Uncertain outcome: {{effect.on_unknown.replaceAll('_',' ')}}</p></li></ol>
    <p>Before target writes, restore the confirmed source only after fencing the target. After target writes, use forward recovery or separately approved, reconciled source return.</p>
    <a v-if="record.content.lane==='isolated_campaign'" class="my-3 inline-block underline" :href="`/tenants/${tenantId}/sites/${record.content.scope.site_id}/applications/${applicationId}/environments/${environment}/jobs/create?plan=${record.id}&digest=${record.binding.digest}`">Run this plan in an isolated simulation campaign</a>
    <Link v-if="record.content.action==='application.migrate' && record.content.lane==='operational'" class="my-3 inline-block underline" :href="`/tenants/${tenantId}/sites/${record.content.scope.site_id}/applications/${applicationId}/environments/${environment}/migration-campaigns`">Plan staggered migration campaigns</Link>
    <button :disabled="!canApprove" @click="send('approval',{plan_id:record.id,plan_digest:record.binding.digest},sites)">Request independent approval for this digest</button>
    <Link class="action secondary" :href="`${base}?revision=${revisionId}`">Reassess current inputs</Link>
    <form class="max-w-2xl" @submit.prevent="send('diff',{plan_id:record.id,other_plan_id:compare},sites)"><label for="compare-plan">Other plan ID<input id="compare-plan" v-model="compare" required maxlength="36" /></label><button :disabled="blocked">Compare plan contents</button></form>
    <section v-if="comparison"><h3 class="font-semibold">Plan differences</h3><p>Approval reusable: {{comparison.approval_reusable?'yes':'no; review the new digest'}}</p><ul><li v-for="change in comparison.changes" :key="change.path" class="break-all">{{change.path}} · {{change.change}}</li></ul><p v-if="!comparison.changes.length">Semantic content is identical. Each plan retains its own approval binding.</p></section>
    <details><summary>Exact mappings, artifacts, budgets and recovery contract</summary><pre class="max-h-96 overflow-auto whitespace-pre-wrap break-all rounded bg-slate-100 p-4 text-xs">{{JSON.stringify(record.content,null,2)}}</pre></details>
  </section>
</CatalogueLayout>
</template>
