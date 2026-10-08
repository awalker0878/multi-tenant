<script setup lang="ts">
import { computed, nextTick, ref } from 'vue';
import { Link, router, useForm } from '@inertiajs/vue3';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';
import type { OperatorField, OperatorWorkspace } from '../../features/inventory/contracts';
import { observedTime, useInventoryAccess } from '../../features/inventory/useAccess';
const props = defineProps<{ tenantId: string; siteId: string; workspace: OperatorWorkspace; notice: string | null }>();
const base = `/tenants/${props.tenantId}/inventory/sites/${props.siteId}`;
const { unavailable } = useInventoryAccess(base + '/operator-inputs/status');
const saved = props.workspace.record;
const values: Record<string, string | number> = { ...(saved?.values ?? {}) };
const form = useForm({ command_key: crypto.randomUUID(), revision: saved?.revision ?? null,
  input: { values, configuration_digest: props.workspace.configuration?.digest ?? null } });
const group = ref(props.workspace.groups[0]?.id ?? 'access');
const fields = computed(() => props.workspace.fields.filter(field => field.group === group.value));
const currentGroup = computed(() => props.workspace.groups.find(item => item.id === group.value));
const supplied = (id: string) => form.input.values[id] !== undefined && form.input.values[id] !== '';
const count = (id: string) => props.workspace.fields.filter(field => field.group === id && supplied(field.id)).length;
const total = (id: string) => props.workspace.fields.filter(field => field.group === id).length;
const completed = computed(() => props.workspace.fields.filter(field => supplied(field.id)).length);
const normalized = () => Object.fromEntries(Object.entries(form.input.values).filter(([, value]) => value !== ''));
const initial = JSON.stringify(values);
const dirty = computed(() => JSON.stringify(normalized()) !== initial);
const errors = computed(() => form.errors as Record<string, string>);
const uncertain = computed(() => errors.value.inventory_status === '503');
const stale = computed(() => ['412', '428'].includes(errors.value.inventory_status));
const blocked = computed(() => form.processing || unavailable.value || uncertain.value || stale.value);
const help: Record<string, string> = {
  required_operator_inputs_missing: 'Required operator inputs are still missing. Each section shows what remains.',
  environment_review_required: 'Collect and confirm the source and destination API findings in Environment configuration.',
  environment_review_changed: 'The environment review changed. Check the current findings and save a new input revision.',
};
function update(field: OperatorField, event: Event) {
  const value = (event.target as HTMLInputElement).value;
  form.input.values[field.id] = field.kind === 'integer' && value !== '' ? Number(value) : value;
}
function submit(retry = false) {
  if (form.processing || unavailable.value || (!retry && (uncertain.value || stale.value))) return;
  if (!retry) { form.clearErrors(); form.command_key = crypto.randomUUID(); }
  form.transform(data => ({ ...data, input: { ...data.input, values: normalized() } })).post(base + '/operator-inputs', {
    preserveState: 'errors', onError: async () => { await nextTick(); document.getElementById('operator-errors')?.focus(); },
  });
}
</script>
<template>
  <CatalogueLayout title="Operator readiness" :tenant-id="tenantId">
    <div class="readiness-intro"><div><p class="max-w-3xl text-sm leading-7 text-slate-600">Prepare the access, recovery and operating information needed to commission this site. API-discovered configuration stays linked to its environment review.</p><div class="mt-3 flex flex-wrap gap-5 text-sm"><Link :href="base" class="text-teal-800 underline">Site inventory</Link><Link :href="base + '/configuration'" class="text-teal-800 underline">Environment configuration</Link><Link :href="base + '/migration'" class="text-teal-800 underline">Workload migration review</Link></div></div><span class="status-tag pending">{{ workspace.collection_complete ? 'Inputs collected · qualification pending' : 'Operator action required' }}</span></div>
    <p v-if="notice" role="status" class="my-5 rounded-lg border border-teal-200 bg-teal-50 p-4 text-sm text-teal-900">{{ notice }}</p>
    <div v-if="Object.keys(errors).length" id="operator-errors" role="alert" tabindex="-1" class="my-5"><p v-for="(error, key) in errors" :key="key">{{ key === 'inventory_status' ? '' : error }}</p><button v-if="uncertain" type="button" :disabled="form.processing || unavailable" @click="submit(true)">Recover unchanged save</button><button v-if="stale" type="button" @click="router.get(base + '/operator-inputs')">Refresh latest record (discards unsaved edits)</button></div>
    <p v-if="unavailable" role="alert" class="my-5">Current access cannot be verified. Saving and downloads are paused.</p>
    <div class="readiness-stats" aria-label="Input collection summary">
      <div class="panel"><span class="metric-label">INPUTS SUPPLIED{{ dirty ? ' · UNSAVED' : '' }}</span><strong>{{ completed }} <small>/ {{ workspace.fields.length }}</small></strong><p>Owner references and operating targets</p></div>
      <div class="panel"><span class="metric-label">ENVIRONMENT REVIEW</span><strong class="text-label">{{ workspace.configuration?.confirmation_current ? 'Confirmed' : 'Review needed' }}</strong><p>{{ workspace.configuration ? `Configuration revision ${workspace.configuration.revision}` : 'Select and discover your environments' }}</p></div>
      <div class="panel"><span class="metric-label">SAVED INPUT PACKET</span><strong class="text-label">{{ saved ? `Revision ${saved.revision}` : 'No saved draft' }}</strong><p>{{ saved ? observedTime(saved.saved_at) : 'Save what you know and return later' }}</p></div>
    </div>
    <div class="readiness-grid">
      <aside class="panel readiness-checklist"><p class="eyebrow">REQUIRED INPUTS</p><h2 class="text-lg font-semibold">Commissioning checklist</h2><p class="mt-2 text-xs leading-6 text-slate-600">All fields are required for collection completeness. Partial drafts can be saved.</p><nav aria-label="Operator input sections" class="mt-5"><button v-for="(item, index) in workspace.groups" :key="item.id" type="button" class="checklist-item" :class="{ selected: group === item.id }" :aria-pressed="group === item.id" @click="group = item.id"><span class="step-number">{{ String(index + 1).padStart(2, '0') }}</span><span class="min-w-0"><strong>{{ item.label }}</strong><small>{{ count(item.id) }} of {{ total(item.id) }} supplied</small></span></button></nav><div class="mt-6 border-t border-slate-200 pt-5"><p class="text-xs font-semibold">Native qualification remains separate</p><p class="mt-2 text-xs leading-6 text-slate-600">Supplying a reference records an input. Its owner must verify the underlying evidence and approve the exact operating scope.</p></div></aside>
      <form class="panel readiness-form" @submit.prevent="submit()">
        <div class="form-section-heading"><div><p class="eyebrow">{{ currentGroup?.owner }}</p><h2 class="text-xl font-semibold">{{ currentGroup?.label }}</h2></div><span class="status-tag">{{ count(group) }} / {{ total(group) }} supplied</span></div>
        <p class="mb-6 text-sm leading-6 text-slate-600">Enter protected record identifiers, such as <code>vault:site-a/source-execution</code> or <code>evidence:review-2026-04</code>. Keep passwords, access tokens and private keys in the approved secret store.</p>
        <fieldset :disabled="blocked" class="operator-fields"><legend class="sr-only">{{ currentGroup?.label }} inputs</legend><div v-for="field in fields" :key="field.id" class="operator-field"><div class="field-label"><label :for="field.id">{{ field.label }}</label><span class="status-tag" :class="supplied(field.id) ? 'supplied' : 'pending'">{{ supplied(field.id) ? 'Supplied' : 'Required' }}</span></div><input :id="field.id" :value="form.input.values[field.id] ?? ''" :type="field.kind === 'integer' ? 'number' : 'text'" :min="field.minimum ?? undefined" :max="field.maximum ?? undefined" :step="field.kind === 'integer' ? 1 : undefined" :maxlength="field.kind === 'reference' ? 240 : undefined" :aria-describedby="field.id + '-help'" autocomplete="off" :placeholder="field.kind === 'integer' ? 'Enter approved target' : 'Enter record identifier'" @input="update(field, $event)" /><p :id="field.id + '-help'" class="field-help">{{ field.help }}</p></div></fieldset>
        <div class="save-bar"><div><button type="submit" :disabled="blocked">Save operator inputs</button><p class="field-help">{{ dirty ? 'You have unsaved changes.' : 'Each save creates an attributable revision.' }}</p></div><a v-if="saved && !dirty && !blocked" :href="base + '/operator-inputs/download'" class="action secondary">Download saved packet</a></div>
      </form>
    </div>
    <section class="panel mt-6" aria-labelledby="remaining-title"><h2 id="remaining-title" class="text-lg font-semibold">Remaining requirements</h2><ul v-if="workspace.holds.length" class="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-600"><li v-for="hold in workspace.holds" :key="hold">{{ help[hold] ?? hold.replaceAll('_', ' ') }}</li></ul><p class="mt-3 text-sm leading-6 text-slate-600">Native testing, evidence validation and independent receiving decisions are still required before commissioning. The downloaded packet supports that handover; it does not enable deployment or migration.</p><p v-if="saved" class="mt-4 break-all font-mono text-xs text-slate-500">Packet SHA-256: {{ saved.digest }}</p></section>
  </CatalogueLayout>
</template>
<style scoped>
.readiness-intro { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; }
.readiness-intro > .status-tag { flex-shrink: 0; margin-top: 5px; }
.readiness-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; margin: 26px 0; }
.metric-label { font-size: 10px; font-weight: 650; color: var(--muted); letter-spacing: .09em; }
.readiness-stats strong { display: block; margin-top: 12px; font-size: 32px; font-weight: 650; letter-spacing: -.025em; }
.readiness-stats strong.text-label { font-size: 22px; margin-top: 18px; margin-bottom: 6px; }
.readiness-stats small { font-size: 18px; color: #788e9d; font-weight: 400; }
.readiness-stats p { margin-top: 8px; font-size: 12px; color: var(--muted); }
.readiness-grid { display: grid; grid-template-columns: 280px minmax(0, 1fr); gap: 22px; align-items: start; }
.readiness-checklist { padding: 24px 18px; }
.catalogue .checklist-item { width: 100%; justify-content: flex-start; gap: 13px; background: transparent; color: var(--ink); padding: 14px 9px; margin-top: 6px; text-align: left; border: 1px solid transparent; }
.catalogue .checklist-item.selected { background: #edf6f6; border-color: #bfdddf; }
.checklist-item strong { display: block; font-size: 12px; line-height: 1.6; font-weight: 650; }
.checklist-item small { display: block; font-size: 11px; color: var(--muted); margin-top: 4px; font-weight: 400; }
.step-number { border: 1px solid #c5d7df; border-radius: 6px; padding: 6px; font-size: 10px; color: #496e7e; }
.form-section-heading { display: flex; justify-content: space-between; align-items: start; gap: 12px; margin-bottom: 16px; }
.form-section-heading .eyebrow { letter-spacing: 0; }
.operator-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px; }
.field-label { display: flex; justify-content: space-between; align-items: start; gap: 8px; }
.field-label label { font-size: 12px; line-height: 1.6; }
.field-label .status-tag { font-size: 9px; padding: 3px 5px; flex-shrink: 0; }
.save-bar { margin-top: 28px; border-top: 1px solid var(--line); padding-top: 18px; display: flex; justify-content: space-between; align-items: start; gap: 16px; }
@media (max-width: 1200px) { .readiness-grid { grid-template-columns: 240px minmax(0, 1fr); } .operator-fields { grid-template-columns: minmax(0, 1fr); } .readiness-intro { flex-direction: column; gap: 8px; } }
@media (max-width: 700px) { .readiness-stats, .readiness-grid { grid-template-columns: minmax(0, 1fr); } .readiness-stats { gap: 12px; } .readiness-stats .panel { padding: 18px; } .readiness-stats strong.text-label { margin-top: 10px; } .save-bar { flex-direction: column; } }
</style>
