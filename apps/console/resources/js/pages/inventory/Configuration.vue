<script setup lang="ts">
import { computed, nextTick } from 'vue';
import { Link, router, useForm } from '@inertiajs/vue3';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';
import type { PortingInput, PortingWorkspace } from '../../features/inventory/contracts';
import { observedTime, useInventoryAccess } from '../../features/inventory/useAccess';
const props = defineProps<{ tenantId: string; siteId: string; workspace: PortingWorkspace; notice: string | null }>();
const base = `/tenants/${props.tenantId}/inventory/sites/${props.siteId}/configuration`;
const { unavailable, now } = useInventoryAccess(base + '/status');
const saved = props.workspace.configuration;
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value));
const initial: PortingInput = { source_endpoint: saved?.source_endpoint ?? null, target_endpoint: saved?.target_endpoint ?? null,
  manual: clone(saved?.manual ?? {}), choices: clone(saved?.choices ?? props.workspace.capabilities.map(c => ({ id: c.id as PortingInput['choices'][number]['id'], required: false, interpretation: 'observed' as const, reason: '' }))) };
const form = useForm({ operation: 'save', command_key: crypto.randomUUID(), revision: saved?.revision ?? null,
  endpoint_id: null as string | null, digest: saved?.digest ?? null, configuration: initial });
const initialJson = JSON.stringify(initial);
const dirty = computed(() => JSON.stringify(form.configuration) !== initialJson);
const errors = computed(() => form.errors as Record<string, string>);
const uncertain = computed(() => errors.value.inventory_status === '503');
const stale = computed(() => errors.value.inventory_status === '412');
const blocked = computed(() => form.processing || unavailable.value || uncertain.value || stale.value);
const expired = computed(() => [props.workspace.source, props.workspace.target].some(s => !s?.current || s.queries.some(q => q.expires_at <= now.value)));
const submit = () => form.post(base, { preserveState: 'errors', onError: async () => { await nextTick(); document.getElementById('configuration-errors')?.focus(); } });
function act(operation: string, endpoint: string | null = null) {
  if (blocked.value) return;
  form.clearErrors(); form.operation = operation; form.endpoint_id = endpoint; form.command_key = crypto.randomUUID(); submit();
}
const manualValue = (id: string) => form.configuration.manual[id as keyof PortingInput['manual']] ?? '';
const updateManual = (id: string, event: Event) => { form.configuration.manual[id as keyof PortingInput['manual']] = (event.target as HTMLInputElement).value; };
const overrideChanged = (index: number) => { if (form.configuration.choices[index].interpretation === 'observed') form.configuration.choices[index].reason = ''; };
</script>
<template>
  <CatalogueLayout title="Environment configuration and porting review" :tenant-id="tenantId">
    <Link :href="`/tenants/${tenantId}/inventory`" class="text-teal-800 underline">Inventory sites</Link>
    <p class="my-4 max-w-4xl">Pull the configured options and installed features from each environment. Review the findings, select what must be ported, and explain any interpretation that differs from the API. Original observations remain visible.</p>
    <p v-if="notice" role="status" class="my-4 rounded border border-teal-600 bg-teal-50 p-4">{{ notice }}</p>
    <div v-if="Object.keys(errors).length" id="configuration-errors" role="alert" tabindex="-1" class="my-4 border border-red-600 p-4"><p v-for="(error, key) in errors" :key="key">{{ key === 'inventory_status' ? '' : error }}</p></div>
    <p v-if="unavailable" role="status">Access cannot currently be checked. Editing is paused until access is available.</p>
    <div class="my-5 flex flex-wrap gap-3">
      <button type="button" class="secondary" :disabled="form.processing" @click="router.get(base)">Refresh findings</button>
      <button v-if="uncertain" type="button" :disabled="form.processing || unavailable" @click="submit">Retry unchanged command</button>
    </div>
    <form @submit.prevent="act('save')">
      <fieldset :disabled="blocked" class="space-y-6">
        <legend class="text-xl font-semibold">1. Environments</legend>
        <p>Select approved connections. Connection addresses and credential references come from the enrolled trust configuration; returned service-catalog addresses cannot redirect collection.</p>
        <p v-if="!workspace.endpoints.length">Enroll a connection from the site inventory to enable API collection. You can save manual inputs while connection setup is pending.</p>
        <Link :href="`/tenants/${tenantId}/inventory/sites/${siteId}`" class="text-teal-800 underline">Manage approved connections</Link>
        <div class="grid gap-5 md:grid-cols-2">
          <div><label for="source-endpoint">Source environment<select id="source-endpoint" v-model="form.configuration.source_endpoint"><option :value="null">Select source</option><option v-for="e in workspace.endpoints" :key="e.id" :value="e.id">{{ e.label }} ({{ e.platform }})</option></select></label><button type="button" class="secondary mt-3" :disabled="!form.configuration.source_endpoint || dirty" @click="act('pull', form.configuration.source_endpoint)">Pull source configuration</button></div>
          <div><label for="target-endpoint">OpenStack destination<select id="target-endpoint" v-model="form.configuration.target_endpoint"><option :value="null">Select destination</option><option v-for="e in workspace.endpoints.filter(e => e.platform === 'openstack')" :key="e.id" :value="e.id">{{ e.label }}</option></select></label><button type="button" class="secondary mt-3" :disabled="!form.configuration.target_endpoint || dirty" @click="act('pull', form.configuration.target_endpoint)">Pull destination configuration</button></div>
        </div>
        <p v-if="dirty" class="text-sm">Save the selected environments and edits before pulling or confirming.</p>
        <h2 class="text-xl font-semibold">2. Features to port</h2>
        <p>“Configured” means resources were returned. “Advertised” means an extension, import method, trait or service was listed. Neither proves the feature works for this workload. Unknown results need API access or further qualification.</p>
        <div class="overflow-x-auto"><table class="w-full text-left"><thead><tr><th class="p-2">Capability</th><th class="p-2">Source API</th><th class="p-2">Destination API</th><th class="p-2">Porting review</th></tr></thead><tbody>
          <tr v-for="(cap, index) in workspace.capabilities" :key="cap.id" class="border-t border-slate-300">
            <td class="p-3"><label :for="'required-' + cap.id" class="flex items-center gap-2"><input :id="'required-' + cap.id" v-model="form.configuration.choices[index].required" type="checkbox" class="w-auto" />{{ cap.label }} required</label></td>
            <td class="p-3">{{ expired ? 'Refresh required' : cap.source_state.replaceAll('_', ' ') }}</td><td class="p-3">{{ expired ? 'Refresh required' : cap.target_state.replaceAll('_', ' ') }}</td>
            <td class="p-3"><label :for="'interpretation-' + cap.id" class="sr-only">{{ cap.label }} interpretation</label><select :id="'interpretation-' + cap.id" v-model="form.configuration.choices[index].interpretation" @change="overrideChanged(index)"><option value="observed">Use API finding</option><option value="include">Include by administrator review</option><option value="exclude">Exclude by administrator review</option></select><label v-if="form.configuration.choices[index].interpretation !== 'observed'" :for="'reason-' + cap.id">Override reason and evidence reference<input :id="'reason-' + cap.id" v-model="form.configuration.choices[index].reason" required maxlength="240" /></label></td>
          </tr>
        </tbody></table></div>
        <h2 class="text-xl font-semibold">3. Inputs outside the standard APIs</h2>
        <p>Supply implementation choices and references for information the APIs cannot determine. Enter references, not passwords, access tokens or private keys.</p>
        <div class="grid gap-4 md:grid-cols-2"><label v-for="field in workspace.manual_fields" :key="field.id" :for="'manual-' + field.id">{{ field.label }}<input :id="'manual-' + field.id" :value="manualValue(field.id)" maxlength="240" @input="updateManual(field.id, $event)" /></label></div>
        <button type="submit">Save revision for review</button>
      </fieldset>
    </form>
    <section class="my-8 rounded-xl border border-slate-300 p-5" aria-labelledby="confirm-title"><h2 id="confirm-title" class="text-xl font-semibold">4. Confirm the saved review</h2>
      <p v-if="saved" class="my-3">Revision {{ saved.revision }} · {{ saved.confirmation_current && !expired ? 'Confirmed' : 'Review required' }}<span v-if="saved.confirmed_at"> · previously confirmed {{ observedTime(saved.confirmed_at) }}</span></p>
      <p>Confirmation acknowledges this revision, its API snapshots, required features, manual values and explained overrides. Native capability qualification and execution approval remain separate.</p>
      <ul v-if="workspace.holds.length" class="my-3 list-disc pl-5"><li v-for="hold in workspace.holds" :key="hold">{{ hold.replaceAll('_', ' ') }}</li></ul>
      <button type="button" class="mt-4" :disabled="blocked || dirty || !saved || expired || workspace.holds.length > 0 || saved.confirmation_current" @click="act('confirm')">Confirm this revision and its disclosed gaps</button>
    </section>
    <section class="my-8" aria-labelledby="api-title"><h2 id="api-title" class="text-xl font-semibold">API observations</h2>
      <div v-for="role in (['source', 'target'] as const)" :key="role" class="my-4"><h3 class="font-semibold capitalize">{{ role }}</h3><p v-if="!workspace[role]">No environment selected.</p><details v-for="query in workspace[role]?.queries ?? []" :key="query.query" class="my-2 rounded border border-slate-300 p-3"><summary>{{ query.query.replaceAll('_', ' ') }} — {{ query.status.replaceAll('_', ' ') }} · {{ query.item_count }} items · {{ observedTime(query.collected_at) }}</summary><p class="my-2 text-sm">Up to five examples are shown. Confirmation binds the complete stored response projection.</p><ul><li v-for="item in query.items" :key="item.id" class="my-3"><strong>{{ item.name }}</strong><dl v-for="attr in item.attributes" :key="attr.key" class="break-words text-sm"><dt>{{ attr.key }}</dt><dd>{{ attr.value }}</dd></dl></li></ul></details></div>
    </section>
    <section class="my-8" aria-labelledby="versions-title"><h2 id="versions-title" class="text-xl font-semibold">OpenStack version qualification — newest first</h2><p class="my-3">Documentation baseline reviewed October 6, 2026. A release or API version does not establish installed backend support. No native environment is qualified by this list.</p><div class="overflow-x-auto"><table class="w-full text-left"><thead><tr><th>Release</th><th>Nova API maximum</th><th>Documentation</th><th>Native qualification</th></tr></thead><tbody><tr v-for="version in workspace.versions" :key="version.release" class="border-t"><td class="p-3"><a :href="version.source" rel="noreferrer" class="text-teal-800 underline">{{ version.release }} {{ version.name }}</a></td><td>{{ version.nova_max }}</td><td>{{ version.documentation.replaceAll('_', ' ') }}</td><td>{{ version.native_qualification.replaceAll('_', ' ') }}</td></tr></tbody></table></div></section>
  </CatalogueLayout>
</template>
