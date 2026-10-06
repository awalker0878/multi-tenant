<script setup lang="ts">
import { computed, ref } from 'vue';
import { Link, useForm } from '@inertiajs/vue3';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';
import type { Job } from '../../features/jobs/contracts';
import { useJob } from '../../features/jobs/useJob';
const props=defineProps<{tenantId:string;base:string;job:Job}>();
const {job,unavailable,now,poll}=useJob(`${props.base}/${props.job.id}/status`,props.job);
const command=useForm({command_key:crypto.randomUUID() as string,action:'',expected_revision:props.job.revision});
const errorMessage=computed(()=>(command.errors as Record<string,string>).command);
const uncertain=ref(false),pending=ref('');
const stale=computed(()=>unavailable.value || !job.value || now.value-job.value.observed_at>20);
const terminal=computed(()=>['completed','cancelled'].includes(job.value?.state??''));
const unknown=computed(()=>job.value?.operations.some(o=>['attempting','outcome_unknown'].includes(o.outcome))??true);
const disabled=computed(()=>stale.value || terminal.value || command.processing || uncertain.value);
const format=(value:string)=>value.replaceAll('_',' ');
function submit(){command.post(`${props.base}/${props.job.id}/commands`,{preserveScroll:true,onSuccess:()=>{pending.value=command.action;uncertain.value=false;void poll();},onError:errors=>{uncertain.value=errors.command_status==='503';void poll();}});}
function request(action:string){if(disabled.value || !job.value)return;command.action=action;command.expected_revision=job.value.revision;command.command_key=crypto.randomUUID();submit();}
</script>
<template>
<CatalogueLayout title="Simulation job" :tenant-id="tenantId">
  <p class="rounded border border-indigo-300 bg-indigo-50 p-3 font-medium">Simulation · E2 evidence · No native platform changes</p>
  <p v-if="stale" role="alert" class="mt-4 rounded border border-amber-600 p-3">Current job state is unavailable. Controls are held until an authorized refresh succeeds.</p>
  <template v-if="job">
    <section class="my-6" aria-labelledby="job-status"><h2 id="job-status" class="text-xl font-semibold">{{ format(job.state) }}</h2>
      <p v-if="job.reason" role="status">{{ format(job.reason) }}</p>
      <p class="mt-2 text-sm text-slate-600">Revision {{ job.revision }} · Updated {{ new Date(job.updated_at*1000).toLocaleString() }}</p>
      <p v-if="unknown" class="mt-3 rounded bg-amber-50 p-3">An effect may have been accepted. Its outcome must be independently reconciled before another attempt. Resource holds remain in place.</p>
      <p v-if="job.recovery_mode==='forward_recovery_required'" class="mt-3">The target write boundary has been reached or may have been reached. Any source return requires a separately approved recovery plan.</p>
      <p v-if="job.cancel_requested">Cancellation was requested. Accepted effects remain recorded and allocations remain held.</p>
      <p v-if="pending" role="status">{{ format(pending) }} request accepted. The workflow will observe the current request at its next safe boundary.</p>
    </section>
    <div class="mb-6 flex flex-wrap gap-2" aria-label="Job controls">
      <button :disabled="disabled" class="rounded border px-3 py-2 disabled:opacity-40" @click="request('pause')">Pause</button>
      <button :disabled="disabled" class="rounded border px-3 py-2 disabled:opacity-40" @click="request('cancel')">Request cancellation</button>
      <button :disabled="disabled" class="rounded border border-red-700 px-3 py-2 disabled:opacity-40" @click="request('stop')">Emergency stop</button>
      <button :disabled="disabled" class="rounded border px-3 py-2 disabled:opacity-40" @click="request('reconcile')">Request reconciliation</button>
      <button :disabled="disabled || unknown || job.cancel_requested" class="rounded border px-3 py-2 disabled:opacity-40" @click="request('resume')">Resume after review</button>
      <button v-if="job.operations.some(o=>o.outcome==='confirmed_failed') && job.recovery_mode!=='forward_recovery_required'" :disabled="disabled || unknown" class="rounded border px-3 py-2 disabled:opacity-40" @click="request('retry_unstarted')">Retry fenced, unstarted attempt</button>
    </div>
    <p v-if="errorMessage" role="alert">{{ errorMessage }}</p>
    <div v-if="uncertain" role="alert"><p>The command response is uncertain. Recover the same receipt before submitting another request.</p><button :disabled="command.processing" class="my-2 rounded border px-3 py-2" @click="submit">Recover command receipt</button></div>
    <section aria-labelledby="effects-title"><h2 id="effects-title" class="text-lg font-semibold">Effect outcomes</h2>
      <ol class="my-3 divide-y rounded border"><li v-for="operation in job.operations" :key="operation.id" class="p-3"><div class="flex flex-wrap justify-between gap-2"><strong>{{ format(operation.step) }}</strong><span>{{ format(operation.outcome) }}</span></div><p v-if="operation.observation?.sealed" class="text-sm text-slate-600">Independent readback sealed this attempt. Observed effects: {{ operation.observation.effect_count }}.</p></li></ol>
    </section>
    <section v-if="job.evidence" class="my-6 rounded border p-4" aria-labelledby="evidence-title"><h2 id="evidence-title" class="text-lg font-semibold">Verified simulation evidence</h2><p>Digest, scope and independent observations were verified by Assurance.</p><dl class="mt-3 space-y-2"><dt>Evidence reference</dt><dd><Link class="underline" :href="`${base}/${job.id}/evidence/${job.evidence.id}`">Inspect verified evidence</Link></dd><dd class="break-all">{{job.evidence.id}}</dd><dt>SHA-256</dt><dd class="break-all font-mono text-sm">{{job.evidence.digest}}</dd><dt>Source revision</dt><dd class="break-all font-mono text-sm">{{job.evidence.source_revision}}</dd></dl><p class="mt-2">Retained until {{new Date(job.evidence.retention_until*1000).toLocaleDateString()}}. This record does not grant native support.</p></section>
    <section class="my-6" aria-labelledby="timeline-title"><h2 id="timeline-title" class="text-lg font-semibold">Job timeline</h2><ol class="mt-3 space-y-2"><li v-for="event in job.events" :key="event.id"><time class="mr-3 text-sm text-slate-500">{{new Date(event.occurred_at*1000).toLocaleTimeString()}}</time>{{format(event.kind)}}</li></ol></section>
    <p class="text-sm text-slate-600">Job {{job.id}} · Plan {{job.plan_id}}. Resource holds remain until an authorized retirement or release procedure establishes safety.</p>
  </template>
</CatalogueLayout>
</template>
