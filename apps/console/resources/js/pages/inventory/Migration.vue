<script setup lang="ts">
import { computed, nextTick, watch } from 'vue';
import { Link, router, useForm } from '@inertiajs/vue3';
import AhvDestination from '../../features/inventory/AhvDestination.vue';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';
import type { MigrationReviewInput, MigrationWorkspace } from '../../features/inventory/contracts';
import { observedTime, useInventoryAccess } from '../../features/inventory/useAccess';
const props = defineProps<{ tenantId: string; siteId: string; profileId?: string | null; workspace: MigrationWorkspace; notice: string | null }>();
const base = `/tenants/${props.tenantId}/inventory/sites/${props.siteId}/migration${props.profileId ? `/profiles/${props.profileId}` : ''}`;
const { unavailable, now } = useInventoryAccess(base + '/status');
const saved = props.workspace.review;
const initial = saved?.input && (!props.profileId || saved.input.source_profile_id === props.profileId) ? saved.input : {
  source_profile_id: props.profileId ?? '', target_profile_id: '', method: '', datasets: [],
  owner_inputs: Object.fromEntries(props.workspace.owner_fields.map(field => [field, ''])) as MigrationReviewInput['owner_inputs'],
  objectives: { owner_id: '', acceptance_sha256: '', max_outage_seconds: 0, max_data_loss_bytes: 0 }, overrides: [],
};
const form = useForm({ operation: 'save', command_key: crypto.randomUUID(), revision: saved?.revision ?? null,
  digest: saved?.digest ?? null, review: JSON.parse(JSON.stringify(initial)) as Omit<MigrationReviewInput, 'method'> & { method: string } });
const dirty = computed(() => JSON.stringify(form.review) !== JSON.stringify(initial));
const errors = computed(() => form.errors as Record<string, string>);
const uncertain = computed(() => errors.value.inventory_status === '503');
const blocked = computed(() => form.processing || unavailable.value || uncertain.value || errors.value.inventory_status === '412');
const source = computed(() => props.workspace.profiles.find(p => p.id === form.review.source_profile_id) ?? (saved?.source.id === form.review.source_profile_id ? saved.source : null));
const target = computed(() => props.workspace.profiles.find(p => p.id === form.review.target_profile_id) ?? (saved?.target.id === form.review.target_profile_id ? saved.target : null));
const disks = computed(() => source.value?.facts.profile_type === 'SourceWorkloadProfile' ? source.value.facts.disks : []);
const ahv = computed(() => target.value?.facts.profile_type === 'TargetCapabilityProfile' && target.value.facts.platform === 'ahv' ? target.value.facts : null);
watch(() => [form.review.source_profile_id, form.review.target_profile_id], (_, previous) => {
  if (!ahv.value) { delete form.review.destination; return; }
  if (!previous && form.review.destination) return;
  form.review.destination = {
    platform: 'ahv', project_id: ahv.value.project_id, prism_central_id: ahv.value.prism_central_id,
    cluster_id: ahv.value.cluster_id, vpc_id: null, storage_container_id: '', category_ids: [], policy_ids: [], firmware: 'bios',
    disks: disks.value.map((d, index) => ({ source_key: d.key, index })),
    nics: (source.value?.facts.profile_type === 'SourceWorkloadProfile' ? source.value.facts.nics : []).map(n => ({ source_key: n.key, quarantine_subnet_id: '', production_subnet_id: '' })),
  };
  form.review.method = 'VM_COLD_EXPORT';
}, { immediate: true });
const expired = computed(() => [source.value, target.value].some(p => !p?.current || p.expires_at <= now.value));
const missing = computed(() => disks.value.filter(d => !form.review.datasets.some(set => set.disk_keys.includes(d.key))));
const submit = () => form.post(base, { preserveState: 'errors', onError: async () => { await nextTick(); document.getElementById('migration-errors')?.focus(); } });
function act(operation: string) { if (blocked.value) return; form.operation = operation; form.command_key = crypto.randomUUID(); form.clearErrors(); submit(); }
function addDataset() { form.review.datasets.push({ id: crypto.randomUUID(), name: '', disk_keys: [], mounts: [''], consistency_group: '', validation_reference: '' }); }
function addOverride() { form.review.overrides.push({ field: 'application_consistency', interpretation: '', reason: '' }); }
</script>
<template>
  <CatalogueLayout title="Migration readiness review" :tenant-id="tenantId">
    <Link :href="`/tenants/${tenantId}/inventory/sites/${siteId}/configuration`" class="text-teal-800 underline">Environment configuration and API collection</Link>
    <Link :href="`/tenants/${tenantId}/inventory/sites/${siteId}/migration-fleet`" class="ml-4 text-teal-800 underline">Source inventory and migration groups</Link>
    <p class="my-4">Review discovered source and destination facts, account for every disk, and select one migration method. Enter application information and references that the platform APIs cannot determine.</p>
    <p v-if="notice" role="status" class="my-4 border border-teal-600 p-4">{{ notice }}</p>
    <div v-if="Object.keys(errors).length" id="migration-errors" role="alert" tabindex="-1" class="my-4 border border-red-600 p-4"><p v-for="(error, key) in errors" :key="key">{{ key === 'inventory_status' ? '' : error }}</p></div>
    <p v-if="unavailable" role="status">Access cannot currently be checked. Editing is paused.</p>
    <div class="my-4 flex gap-3"><button type="button" class="secondary" :disabled="form.processing" @click="router.get(base)">Refresh findings</button><button v-if="uncertain" type="button" :disabled="form.processing || unavailable" @click="submit">Retry unchanged command</button></div>
    <p v-if="!workspace.profiles.length">No current workload profiles have been collected. Pull the enrolled source and target connections with their migration profile streams enabled.</p>
    <form @submit.prevent="act('save')"><fieldset :disabled="blocked" class="space-y-5">
      <legend class="text-xl font-semibold">Source, destination and method</legend>
      <div class="grid gap-4 md:grid-cols-2">
        <label>Source VM profile<select v-model="form.review.source_profile_id" :disabled="!!profileId" required><option value="">Select observed source</option><option v-if="saved && !workspace.profiles.some(p => p.id === saved?.source.id)" :value="saved.source.id">{{ saved.source.native_id }} — refresh required</option><option v-for="p in workspace.profiles.filter(p => p.profile_type === 'SourceWorkloadProfile')" :key="p.id" :value="p.id">{{ p.facts.platform }} · {{ p.native_id }} · {{ observedTime(p.collected_at) }}{{ p.current ? '' : ' · stale' }}</option></select></label>
        <label>Destination profile<select v-model="form.review.target_profile_id" required><option value="">Select observed destination</option><option v-if="saved && !workspace.profiles.some(p => p.id === saved?.target.id)" :value="saved.target.id">{{ saved.target.native_id }} — refresh required</option><option v-for="p in workspace.profiles.filter(p => p.profile_type === 'TargetCapabilityProfile')" :key="p.id" :value="p.id">{{ p.facts.platform }} · {{ p.native_id }} · {{ observedTime(p.collected_at) }}{{ p.current ? '' : ' · stale' }}</option></select></label>
      </div>
      <label>Explicit migration method<select v-model="form.review.method" required><option value="">Select a method</option><option v-for="method in (ahv ? ['VM_COLD_EXPORT'] : workspace.methods)" :key="method" :value="method">{{ method.replaceAll('_', ' ') }}</option></select></label>
      <p>Methods require their own qualification. A failed method never selects another method automatically. Cold export retains the source outage throughout movement; delta methods require a qualified final synchronization protocol.</p>
      <AhvDestination v-if="ahv && form.review.destination" v-model="form.review.destination" :profile="ahv" :source-firmware="source?.facts.profile_type === 'SourceWorkloadProfile' ? source.facts.firmware : null" />
      <h2 class="text-xl font-semibold">All disks and application datasets</h2>
      <table class="w-full text-left"><thead><tr><th>Disk key</th><th>Capacity (bytes)</th><th>Dataset coverage</th></tr></thead><tbody><tr v-for="disk in disks" :key="disk.key" class="border-t"><td class="p-2">{{ disk.key }}</td><td>{{ disk.capacity_bytes ?? 'Unknown' }}</td><td>{{ missing.some(d => d.key === disk.key) ? 'Mapping required' : 'Accounted for' }}</td></tr></tbody></table>
      <p v-if="missing.length" role="status">{{ missing.length }} disks still require dataset mapping.</p>
      <fieldset v-for="(dataset, index) in form.review.datasets" :key="dataset.id" class="rounded border border-slate-300 p-4"><legend>Dataset {{ index + 1 }}</legend>
        <div class="grid gap-4 md:grid-cols-2"><label>Name<input v-model="dataset.name" required maxlength="240" /></label><label>Consistency group<input v-model="dataset.consistency_group" required maxlength="240" /></label><label>Mounts or dataset paths (one per line)<textarea :value="dataset.mounts.join('\n')" required @input="dataset.mounts = ($event.target as HTMLTextAreaElement).value.split('\n')"></textarea></label><label>Correctness check reference<input v-model="dataset.validation_reference" required maxlength="240" /></label></div>
        <fieldset class="my-3"><legend>Disks containing this dataset</legend><label v-for="disk in disks" :key="disk.key" class="mr-4 inline-flex gap-2"><input v-model="dataset.disk_keys" type="checkbox" :value="disk.key" class="w-auto" />Disk {{ disk.key }}</label></fieldset>
        <button type="button" class="secondary" @click="form.review.datasets.splice(index, 1)">Remove dataset</button>
      </fieldset>
      <button type="button" class="secondary" :disabled="!disks.length || form.review.datasets.length >= 256" @click="addDataset">Add dataset</button>
      <h2 class="text-xl font-semibold">Application and operating inputs</h2><p>Use owner-approved references. API identities, versions, devices, capacities and readiness holds remain unchanged.</p>
      <div class="grid gap-4 md:grid-cols-2"><label v-for="field in workspace.owner_fields" :key="field" class="capitalize">{{ field.replaceAll('_', ' ') }}<input v-model="form.review.owner_inputs[field]" required maxlength="240" /></label></div>
      <h2 class="text-xl font-semibold">Owner objectives</h2><div class="grid gap-4 md:grid-cols-2"><label>Application owner ID<input v-model="form.review.objectives.owner_id" required /></label><label>Acceptance record SHA-256<input v-model="form.review.objectives.acceptance_sha256" required pattern="[0-9a-f]{64}" /></label><label>Maximum outage (seconds)<input v-model.number="form.review.objectives.max_outage_seconds" type="number" min="1" max="31536000" required /></label><label>Maximum data loss (bytes)<input v-model.number="form.review.objectives.max_data_loss_bytes" type="number" min="0" max="9007199254740991" required /></label></div>
      <h2 class="text-xl font-semibold">Reasoned application interpretations</h2><div v-for="(override, index) in form.review.overrides" :key="index" class="grid gap-3 rounded border p-4 md:grid-cols-3"><label>Application field<select v-model="override.field"><option v-for="field in workspace.owner_fields" :key="field" :value="field">{{ field.replaceAll('_', ' ') }}</option></select></label><label>Interpretation<input v-model="override.interpretation" required maxlength="240" /></label><label>Reason and evidence<input v-model="override.reason" required maxlength="240" /></label><button type="button" class="secondary" @click="form.review.overrides.splice(index, 1)">Remove interpretation</button></div>
      <button type="button" class="secondary" :disabled="form.review.overrides.length >= 8" @click="addOverride">Add reasoned interpretation</button>
      <div><button type="submit" :disabled="!source || !target || !form.review.datasets.length || missing.length > 0">Save migration review</button></div>
    </fieldset></form>
    <section class="my-8 rounded border border-slate-300 p-5"><h2 class="text-xl font-semibold">Confirm the saved review</h2><p v-if="saved">Revision {{ saved.revision }} · {{ saved.confirmation_current && !expired ? 'Confirmed' : 'Review required' }}</p><p class="my-3">Confirmation binds the exact observations, complete disk and dataset map, method and owner inputs. It does not start a migration.</p><ul v-if="saved?.holds.length" class="my-3 list-disc pl-5"><li v-for="hold in saved.holds" :key="hold">{{ hold.replaceAll('_', ' ') }}</li></ul><button type="button" :disabled="blocked || dirty || !saved || expired || saved.holds.length > 0 || saved.confirmation_current" @click="act('confirm')">Confirm migration review</button></section>
    <section class="my-8"><h2 class="text-xl font-semibold">Original API observations</h2><details v-for="p in [source, target].filter(Boolean)" :key="p!.id" class="my-3 rounded border p-4"><summary>{{ p!.native_id }} · {{ p!.current && p!.expires_at > now ? 'Current' : 'Refresh required' }}</summary><p class="my-3 break-all">Profile {{ p!.digest }}</p><ul class="list-disc pl-5"><li v-for="hold in p!.facts.holds" :key="hold">{{ hold.replaceAll('_', ' ') }}</li></ul><pre class="mt-3 max-h-96 overflow-auto text-sm">{{ JSON.stringify(p!.facts, null, 2) }}</pre></details></section>
  </CatalogueLayout>
</template>
