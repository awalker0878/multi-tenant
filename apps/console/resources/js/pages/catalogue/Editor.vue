<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue';
import { Link, router, useForm } from '@inertiajs/vue3';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';
import WorkloadEditor from '../../features/catalogue/WorkloadEditor.vue';
import RequirementsEditor from '../../features/catalogue/RequirementsEditor.vue';
import { intent as emptyIntent, workload, differences } from '../../features/catalogue/defaults';
import type { Intent, Application, Revision, ReferencePage } from '../../features/catalogue/contracts';
const props = defineProps<{ tenantId: string; environment: string | null; application: Application | null; revision: Revision | null; references: { environments: ReferencePage; wsds: ReferencePage; domains: ReferencePage }; actorId: string; canWrite: boolean }>();
const draft = ref<Intent>(structuredClone(props.revision?.intent ?? emptyIntent(props.actorId)));
const original = JSON.stringify(draft.value);
const mode = ref<'form' | 'import'>('form');
const imported = ref('');
const form = useForm({ name: props.application?.name ?? '', intent_json: '', command_key: crypto.randomUUID(), etag: props.application?.etag ?? null });
const unknown = ref(false), changed = ref(false), reviewed = ref(false);
const changedFields = computed(() => differences(props.revision?.intent, draft.value));
const dirty = computed(() => imported.value !== '' || JSON.stringify(draft.value) !== original || (props.application === null && form.name !== ''));
const newId = () => crypto.randomUUID();
const submit = () => {
 if (!unknown.value) form.intent_json = mode.value === 'import' ? imported.value : JSON.stringify(draft.value);
 form.post(`/tenants/${props.tenantId}/applications${props.application ? '/' + props.application.id + '/revisions' : ''}`, { preserveScroll: true,
  onError: async errors => { unknown.value = errors.catalogue_status === '503'; changed.value = errors.catalogue_status === '412'; await nextTick(); document.getElementById('catalogue-errors')?.focus(); } });
};
const loadFile = async (e: Event) => {
 const file = (e.target as HTMLInputElement).files?.[0]; if (!file) return;
 if (file.size > 262144) { form.setError('intent_json', 'Choose an intent file no larger than 256 KiB.'); return; }
 imported.value = await file.text(); mode.value = 'import';
};
const refresh = () => { reviewed.value = false; router.get(window.location.pathname, { environment: props.revision?.intent.environment.id ?? props.environment }, { only: ['application', 'revision', 'canWrite'], preserveState: true, preserveScroll: true, onSuccess: () => { reviewed.value = true; } }); };
const adopt = () => { form.etag = props.application?.etag ?? null; form.command_key = crypto.randomUUID(); changed.value = false; reviewed.value = false; form.clearErrors(); };
const chooseEnvironment = (e: Event) => { const item = props.references.environments.references.find(r => r.id === (e.target as HTMLSelectElement).value); if (item) draft.value.environment = { id: item.id, version: item.version }; };
let timer: ReturnType<typeof setInterval> | undefined, active = true, removeBefore: (() => void) | undefined;
const check = async () => {
 if (!props.application || document.hidden || unknown.value) return;
 try { const response = await fetch(`/tenants/${props.tenantId}/applications/${props.application.id}/status${props.environment ? '?environment=' + props.environment : ''}`, { headers: { Accept: 'application/json' }, credentials: 'same-origin', cache: 'no-store' });
  if (!active) return;
  if (response.status === 403 || response.redirected) { active = false; router.cancelAll(); router.clearHistory(); window.location.replace('/account'); return; }
  if (response.ok) { const result = await response.json() as { etag: string }; if (active && result.etag !== form.etag) changed.value = true; }
 } catch { /* The owner rechecks current authority on every publication. */ }
};
const beforeUnload = (e: BeforeUnloadEvent) => { if (dirty.value && !form.processing) e.preventDefault(); };
onMounted(() => { timer = setInterval(() => { void check(); }, 15000); window.addEventListener('beforeunload', beforeUnload); removeBefore = router.on('before', e => { if (e.detail.visit.method === 'get' && e.detail.visit.url.pathname !== window.location.pathname && dirty.value && !form.processing && !window.confirm('Discard the unsaved application draft?')) e.preventDefault(); }); });
onUnmounted(() => { active = false; if (timer) clearInterval(timer); removeBefore?.(); window.removeEventListener('beforeunload', beforeUnload); });
</script>
<template>
 <CatalogueLayout :title="application ? 'Revise ' + application.name : 'Create application'" :tenant-id="tenantId">
  <p class="mb-5 text-slate-600">Publish the complete requested intent. Drafts stay in this tab. Do not include passwords, keys or credentials.</p>
  <div v-if="Object.keys(form.errors).length" id="catalogue-errors" role="alert" tabindex="-1"><p>{{ form.errors.intent_json || Object.values(form.errors)[0] }}</p></div>
  <div v-if="changed" class="my-5 rounded-lg border border-amber-700 bg-amber-50 p-4" role="status"><p>The application changed. Your draft is preserved.</p><button type="button" class="secondary" @click="refresh">Review current version</button><template v-if="reviewed"><p class="mt-3">Review the differences below before using the current version as the base.</p><ul class="mt-2 max-h-64 overflow-auto"><li v-for="difference in changedFields" :key="difference.path" class="break-all text-sm">{{ difference.path }} — current: {{ difference.before }}; your draft: {{ difference.after }}</li></ul><button type="button" @click="adopt">Use reviewed current version as base</button></template></div>
  <p v-if="!canWrite" role="alert">You currently have read access. Publishing requires an application author grant.</p>
  <form @submit.prevent="submit">
   <fieldset :disabled="unknown || form.processing || !canWrite" class="space-y-6">
    <label for="application-name">Application name<input id="application-name" v-model="form.name" required maxlength="200" :readonly="application !== null" /></label>
    <div class="flex flex-wrap gap-3"><button type="button" class="secondary" :aria-pressed="mode === 'form'" @click="mode = 'form'">Edit fields</button><button type="button" class="secondary" :aria-pressed="mode === 'import'" @click="mode = 'import'">Import complete intent</button></div>
    <section v-if="mode === 'import'"><label for="intent-file">Intent JSON file<input id="intent-file" type="file" accept="application/json,.json" @change="loadFile" /></label><label for="intent-import" class="mt-4">Complete intent document<textarea id="intent-import" v-model="imported" rows="20" maxlength="262144" required spellcheck="false" class="font-mono text-sm" /></label><p class="mt-2 text-sm">The owner validates the complete document before accepting a revision. Import retains explicit IDs and requirements.</p></section>
    <template v-else>
     <div class="grid gap-4 sm:grid-cols-2"><label for="environment">Environment<select id="environment" :value="draft.environment.id" required @change="chooseEnvironment"><option value="">Choose an environment</option><option v-for="item in references.environments.references.filter(r => !r.retired)" :key="item.id" :value="item.id">{{ item.definition.name }} · version {{ item.version }}</option><option v-if="draft.environment.id && !references.environments.references.some(r => r.id === draft.environment.id)" :value="draft.environment.id">{{ draft.environment.id }}</option></select></label><label for="service-owner">Accountable service owner ID<input id="service-owner" v-model="draft.service_owner_id" required /></label></div>
     <p v-if="references.environments.next_cursor || references.wsds.next_cursor || references.domains.next_cursor" class="text-sm">More reference definitions are available in <Link :href="`/tenants/${tenantId}/catalogue-references`" class="underline">Environments and domains</Link>. Use their IDs and versions when importing intent.</p>
     <section class="space-y-3"><h2 class="text-xl font-semibold">Acceptance criteria</h2><label v-for="(_, index) in draft.acceptance_criteria" :key="index">Criterion {{ index + 1 }}<input v-model="draft.acceptance_criteria[index]" required maxlength="500" /></label><button type="button" class="secondary" :disabled="draft.acceptance_criteria.length >= 50" @click="draft.acceptance_criteria.push('')">Add acceptance criterion</button></section>
     <section class="space-y-4"><h2 class="text-xl font-semibold">Workloads</h2><div v-for="(item, index) in draft.workloads" :key="item.id"><WorkloadEditor v-model="draft.workloads[index]!" :index="index" :wsds="references.wsds.references" :domains="references.domains.references" :datasets="draft.datasets" /><button type="button" class="secondary" :disabled="draft.workloads.length === 1" @click="draft.workloads.splice(index, 1)">Remove workload {{ index + 1 }}</button></div><button type="button" :disabled="draft.workloads.length >= 100" @click="draft.workloads.push(workload())">Add workload</button></section>
     <section class="space-y-4"><h2 class="text-xl font-semibold">Datasets and recovery</h2>
      <fieldset v-for="(data, index) in draft.datasets" :key="data.id" class="grid gap-3 rounded-lg border border-slate-300 p-4 sm:grid-cols-2"><legend>Dataset {{ index + 1 }}</legend><label>Dataset name<input v-model="data.name" required maxlength="200" /></label><label>Data owner ID<input v-model="data.owner_id" required /></label><label>Consistency group<input v-model="data.consistency_group" required maxlength="128" /></label><label>Consistency<select v-model="data.consistency"><option>application</option><option>crash</option><option>quiesced</option></select></label><label>Recovery point objective (seconds)<input v-model.number="data.recovery.rpo_seconds" type="number" min="0" max="31536000" required /></label><label>Recovery time objective (seconds)<input v-model.number="data.recovery.rto_seconds" type="number" min="0" max="31536000" required /></label><label>Recovery method<input v-model="data.recovery.method" required maxlength="128" /></label><label>Recovery strength<select v-model="data.recovery.strength"><option>required</option><option>preferred</option><option>optional</option></select></label><button type="button" class="secondary" @click="draft.datasets.splice(index,1)">Remove dataset {{ index + 1 }}</button></fieldset>
      <button type="button" class="secondary" :disabled="draft.datasets.length >= 200" @click="draft.datasets.push({ id:newId(), name:'', owner_id:actorId, consistency_group:'', consistency:'application', recovery:{rpo_seconds:0,rto_seconds:3600,method:'application_rebuild_restore',strength:'required'} })">Add dataset</button>
     </section>
     <section class="space-y-4"><h2 class="text-xl font-semibold">Dependencies and communication</h2>
      <fieldset v-for="(edge, index) in draft.dependencies" :key="index" class="grid gap-3 rounded-lg border border-slate-300 p-4 sm:grid-cols-2"><legend>Dependency {{ index + 1 }}</legend><label>Dependent workload<select v-model="edge.from" required><option value="">Choose</option><option v-for="w in draft.workloads" :key="w.id" :value="w.id">{{ w.name }}</option></select></label><label>Required workload<select v-model="edge.to" required><option value="">Choose</option><option v-for="w in draft.workloads" :key="w.id" :value="w.id">{{ w.name }}</option></select></label><label>Dependency type<select v-model="edge.kind"><option>startup</option><option>shutdown</option><option>communication</option></select></label><label>Readiness condition<input v-model="edge.readiness" required maxlength="500" /></label><label>Protocol<select v-model="edge.protocol"><option>none</option><option>tcp</option><option>udp</option><option>icmp</option></select></label><label>Port (TCP/UDP)<input v-model.number="edge.port" type="number" min="1" max="65535" /></label><label>Dataset<select v-model="edge.dataset_id"><option :value="null">None</option><option v-for="d in draft.datasets" :key="d.id" :value="d.id">{{ d.name }}</option></select></label><label>Dependency strength<select v-model="edge.strength"><option>required</option><option>preferred</option><option>optional</option></select></label><label><input v-model="edge.controlled_interface" type="checkbox" />Controlled inter-domain interface required</label><button type="button" class="secondary" @click="draft.dependencies.splice(index,1)">Remove dependency {{ index + 1 }}</button></fieldset>
      <button type="button" class="secondary" :disabled="draft.dependencies.length >= 500" @click="draft.dependencies.push({from:'',to:'',kind:'startup',readiness:'',protocol:'none',port:null,controlled_interface:false,dataset_id:null,strength:'required'})">Add dependency</button>
     </section>
     <section class="space-y-4"><h2 class="text-xl font-semibold">Shared service requirements</h2><fieldset v-for="(service,index) in draft.services" :key="index" class="space-y-3 rounded-lg border border-slate-300 p-4"><legend>Service {{ index + 1 }}</legend><label>Service name<input v-model="service.name" required maxlength="128" /></label><label>Service owner ID<input v-model="service.owner_id" required /></label><label>Workload<select v-model="service.workload_id" required><option value="">Choose</option><option v-for="w in draft.workloads" :key="w.id" :value="w.id">{{ w.name }}</option></select></label><RequirementsEditor v-model="service.requirements" :id="`service-${index}`" /><button type="button" class="secondary" @click="draft.services.splice(index,1)">Remove service {{ index + 1 }}</button></fieldset><button type="button" class="secondary" :disabled="draft.services.length >= 100" @click="draft.services.push({name:'',owner_id:actorId,workload_id:'',requirements:[]})">Add shared service</button></section>
     <section class="space-y-3"><h2 class="text-xl font-semibold">Application requirements</h2><p class="text-sm">Required controls remain part of intent even when a platform cannot support them. Planning will explain their fit.</p><RequirementsEditor v-model="draft.requirements" id="application-requirements" /></section>
    </template>
   </fieldset>
   <div class="mt-7 border-t border-slate-300 pt-4"><p v-if="unknown" role="status">The last result is uncertain. Fields are locked so the same command can be retried safely.</p><button type="submit" :disabled="form.processing || !canWrite || changed">{{ unknown ? 'Retry unchanged command' : application ? 'Publish new revision' : 'Create application' }}</button></div>
  </form>
 </CatalogueLayout>
</template>
