<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue';
import { Link, router, useForm } from '@inertiajs/vue3';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';
import type { EndpointList, MigrationCandidate, MigrationFleet, MigrationGroupDetail } from '../../features/inventory/contracts';
import { observedTime, useInventoryAccess } from '../../features/inventory/useAccess';
import { migrationHold } from '../../features/inventory/migration-holds';

const props = defineProps<{ tenantId: string; siteId: string; workspace: MigrationFleet; detail: MigrationGroupDetail | null; endpoints: EndpointList; notice: string | null }>();
const base = `/tenants/${props.tenantId}/inventory/sites/${props.siteId}/migration-fleet`;
const siteBase = `/tenants/${props.tenantId}/inventory/sites/${props.siteId}`;
const { now, unavailable } = useInventoryAccess(base + '/status');
const group = props.detail?.group;
const rows = ref<MigrationCandidate[]>([...new Map([...props.workspace.items, ...(props.detail?.members.map(m => m.candidate) ?? [])].map(m => [m.resource_id, m])).values()]);
const cursor = ref(props.workspace.next_cursor);
const query = ref('');
const grouping = ref<'endpoint_label' | 'guest_id' | 'power_state' | 'readiness'>('endpoint_label');
const readiness = ref('all');
const loading = ref(false);
const running = ref(false);
const message = ref('');
const results = ref<Record<string, { status: string; reason: string }>>({});
const bindings = ref<Record<string, unknown>>({});
type PlanOption = { recipe_id: string; base_plan_id: string; mode: string; method: string; expires_at: number; stages: number };
const planOptions = ref<Record<string, PlanOption[]>>({});
const choices = ref<Record<string, string>>({});
const plans = ref<Record<string, string>>({});
const pending = ref<Record<string, { command_key: string; base_plan_id: string; recipe_id: string }>>({});
const planSelectionReady = computed(() => Object.entries(choices.value).some(([id, recipe]) => recipe && !plans.value[id]));
const controller = new AbortController();
onUnmounted(() => controller.abort());
const form = useForm({ command_key: crypto.randomUUID(), revision: group?.revision ?? null,
  selection: { name: group?.input.name ?? '', application_id: group?.input.application_id ?? '', environment_id: group?.input.environment_id ?? '',
    target_profile_id: group?.input.target_profile_id ?? '', format: group?.input.format ?? 'qcow2', resource_ids: group?.input.members.map(m => m.resource_id) ?? [] } });
const refreshForm = useForm({ endpoint_id: '', command_key: crypto.randomUUID() });
const errors = computed(() => ({ ...form.errors, ...refreshForm.errors }) as Record<string, string>);
const uncertain = computed(() => errors.value.inventory_status === '503');
const blocked = computed(() => running.value || loading.value || form.processing || refreshForm.processing || unavailable.value || uncertain.value || errors.value.inventory_status === '412');
const initial = JSON.stringify(form.selection);
const dirty = computed(() => JSON.stringify(form.selection) !== initial);
const selected = computed(() => rows.value.filter(r => form.selection.resource_ids.includes(r.resource_id)));
const visible = computed(() => rows.value.filter(r => {
  const match = [r.name, r.native_id, r.endpoint_label, r.native_scope, r.guest_id ?? '', r.power_state ?? ''].join(' ').toLowerCase().includes(query.value.toLowerCase());
  return match && (readiness.value === 'all' || (readiness.value === 'held' ? r.holds.length > 0 || r.expires_at <= now.value : r.holds.length === 0 && r.expires_at > now.value));
}));
const sections = computed(() => {
  const sets: Record<string, MigrationCandidate[]> = {};
  for (const vm of visible.value) { const key = vm[grouping.value] ?? 'Not discovered'; (sets[key] ??= []).push(vm); }
  return Object.entries(sets).sort(([a], [b]) => a.localeCompare(b));
});
const targets = computed(() => props.workspace.targets.filter(t => t.current && t.expires_at > now.value));
const selectedTarget = computed(() => targets.value.find(t => t.id === form.selection.target_profile_id));
const totalMemory = computed(() => selected.value.reduce((total, vm) => total + (vm.memory_mb ?? 0), 0));
const totalCpu = computed(() => selected.value.reduce((total, vm) => total + (vm.cpu ?? 0), 0));
const totalDisk = computed(() => selected.value.reduce((total, vm) => total + (vm.disk_bytes ?? 0), 0));
const reviewUrl = (id: string) => `${siteBase}/migration/profiles/${id}`;
function selectRows(items: MigrationCandidate[]) {
  const next = [...new Set([...form.selection.resource_ids, ...items.map(i => i.resource_id)])];
  if (next.length > 50) { message.value = 'A migration group can contain up to 50 VMs. Narrow your selection or create another group.'; return; }
  form.selection.resource_ids = next; message.value = '';
}
function save() {
  if (blocked.value) return;
  form.command_key = crypto.randomUUID(); form.clearErrors(); submit();
}
function submit() { form.post(base + '/groups' + (group ? `/${group.id}` : ''), { preserveState: 'errors' }); }
function refreshApi() {
  if (blocked.value || !refreshForm.endpoint_id) return;
  refreshForm.command_key = crypto.randomUUID(); refreshForm.clearErrors();
  refreshForm.post(base + '/refresh', { preserveState: 'errors' });
}
function accessLost(response: Response) {
  if (response.type === 'opaqueredirect' || [401, 403, 404, 419].includes(response.status)) {
    controller.abort(); router.clearHistory(); window.location.replace('/account'); return true;
  }
  return false;
}
async function loadMore() {
  if (blocked.value || !cursor.value) return;
  loading.value = true;
  try {
    const response = await fetch(base + '/page?cursor=' + encodeURIComponent(cursor.value), { credentials: 'same-origin', cache: 'no-store', redirect: 'manual', headers: { Accept: 'application/json' }, signal: controller.signal });
    if (accessLost(response)) return;
    if (!response.ok) throw new Error();
    const page = await response.json() as MigrationFleet;
    rows.value = [...new Map([...rows.value, ...page.items].map(vm => [vm.resource_id, vm])).values()]; cursor.value = page.next_cursor;
  } catch { message.value = 'Inventory could not be loaded. Refresh before changing the selection.'; }
  finally { loading.value = false; }
}
async function prepareGroup() {
  if (blocked.value || dirty.value || !group || !props.detail) return;
  running.value = true; message.value = ''; results.value = {}; bindings.value = {};
  try {
    for (const member of props.detail.members) {
      const id = member.candidate.resource_id;
      if (controller.signal.aborted) break;
      results.value[id] = { status: 'Checking', reason: '' };
      // Inventory re-reads this exact group and member; no browser-supplied disk or authority facts.
      const token = document.cookie.split('; ').find(c => c.startsWith('XSRF-TOKEN='))?.slice('XSRF-TOKEN='.length) ?? '';
      const response = await fetch(`${base}/groups/${group.id}/prepare`, { method: 'POST', credentials: 'same-origin', cache: 'no-store', redirect: 'manual', signal: controller.signal,
        headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-XSRF-TOKEN': decodeURIComponent(token) },
        body: JSON.stringify({ revision: group.revision, digest: group.digest, resource_id: id }) });
      if (accessLost(response)) break;
      const result = await response.json() as { error?: string; holds?: string[]; binding?: unknown; native_write_authorized?: boolean };
      if (response.ok && result.binding && result.native_write_authorized === false) {
        results.value[id] = { status: 'Prepared', reason: 'Current VM review and disk mappings verified by Planning.' }; bindings.value[id] = result.binding;
      } else {
        results.value[id] = { status: 'Held', reason: (result.holds ?? [result.error ?? 'preparation_unavailable']).map(migrationHold).join(' ') };
        if (response.status === 412 || response.status >= 500) { message.value = 'Batch paused. Refresh current findings before preparing again.'; break; }
      }
    }
  } catch { message.value = 'Preparation interrupted. Refresh and retry; preparation does not submit a migration job.'; }
  finally { running.value = false; }
}
function planUrl(id: string) {
  return `/tenants/${props.tenantId}/applications/${group!.input.application_id}/environments/${group!.input.environment_id}/planning/plans/${id}?sites=${props.siteId}`;
}
async function completeGroup(operation: 'options' | 'compose') {
  if (blocked.value || dirty.value || !group || !props.detail) return;
  running.value = true; message.value = '';
  try {
    for (const member of props.detail.members) {
      const id = member.candidate.resource_id;
      if (controller.signal.aborted) break;
      if (plans.value[id] || (operation === 'compose' && !choices.value[id])) continue;
      if (operation === 'compose' && !pending.value[id]) {
        const choice = planOptions.value[id]?.find(o => o.recipe_id === choices.value[id] && o.expires_at > now.value);
        if (!choice) { results.value[id] = { status: 'Held', reason: 'Refresh current plan choices.' }; continue; }
        pending.value[id] = { command_key: crypto.randomUUID(), base_plan_id: choice.base_plan_id, recipe_id: choice.recipe_id };
      }
      results.value[id] = { status: operation === 'options' ? 'Finding plans' : 'Creating plan', reason: '' };
      const token = document.cookie.split('; ').find(c => c.startsWith('XSRF-TOKEN='))?.slice('XSRF-TOKEN='.length) ?? '';
      const response = await fetch(`${base}/groups/${group.id}/prepare`, { method: 'POST', credentials: 'same-origin', cache: 'no-store', redirect: 'manual', signal: controller.signal,
        headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-XSRF-TOKEN': decodeURIComponent(token) },
        body: JSON.stringify({ operation, revision: group.revision, digest: group.digest, resource_id: id, ...(operation === 'compose' ? pending.value[id] : {}) }) });
      if (accessLost(response)) break;
      const result = await response.json() as { items?: PlanOption[]; id?: string; kind?: string; binding?: unknown; native_write_authorized?: boolean; error?: string; holds?: string[] };
      if (response.ok && result.native_write_authorized === false && operation === 'options' && Array.isArray(result.items)) {
        planOptions.value[id] = result.items;
        if (!pending.value[id]) choices.value[id] = result.items.length === 1 ? result.items[0].recipe_id : '';
        results.value[id] = { status: result.items.length ? 'Choose plan' : 'Held', reason: result.items.length ? 'Select the migration mode to create for review.' : 'No current commissioned recipe and base plan match this VM. Complete platform commissioning and Planning assessment.' };
      } else if (response.ok && result.native_write_authorized === false && operation === 'compose' && result.id && result.kind === 'plan' && result.binding) {
        plans.value[id] = result.id; bindings.value[id] = result.binding; delete pending.value[id];
        results.value[id] = { status: 'Plan created', reason: 'Review the complete plan and request independent approval.' };
      } else {
        results.value[id] = { status: 'Held', reason: (result.holds ?? [result.error ?? 'planning_unavailable']).map(migrationHold).join(' ') };
        if (response.status >= 500 || response.status === 412 || response.ok) {
          message.value = operation === 'compose' ? 'Batch paused. Retry plan creation unchanged to resolve an uncertain result.' : 'Batch paused. Refresh current findings before finding plans again.'; break;
        }
        // An explicit rejection committed no plan; an uncertain response retains the same command.
        if (operation === 'compose') delete pending.value[id];
      }
    }
  } catch { message.value = operation === 'compose' ? 'Plan creation interrupted. Retry unchanged; completed plans are preserved.' : 'Plan lookup interrupted. Refresh current findings and retry.'; }
  finally { running.value = false; }
}
</script>

<template>
  <CatalogueLayout title="Migrate virtual machines" :tenant-id="tenantId">
    <Link v-if="group" :href="`/tenants/${tenantId}/applications/${group.input.application_id}/environments/${group.input.environment_id}/planning/migration-support/${siteId}`" class="mb-4 block text-teal-800 underline">Review directional support and qualification</Link>
    <div class="flex flex-wrap gap-4"><Link :href="siteBase" class="text-teal-800 underline">Site inventory</Link><Link :href="siteBase + '/configuration'" class="text-teal-800 underline">Source and target connections</Link></div>
    <p class="my-4 max-w-4xl">Discover source VMs through the enrolled platform APIs, organize them into migration groups, and prepare selected machines for the selected destination. Each VM keeps its own disk mapping, method and readiness review.</p>
    <p v-if="notice" role="status" class="my-4 rounded border border-teal-600 bg-teal-50 p-4">{{ notice }}</p>
    <div v-if="Object.keys(errors).length" role="alert" class="my-4 rounded border border-red-600 p-4"><p v-for="(error, key) in errors" :key="key">{{ key === 'inventory_status' ? '' : error }}</p><button v-if="uncertain" :disabled="form.processing || refreshForm.processing || unavailable" @click="Object.keys(form.errors).length ? submit() : refreshForm.post(base + '/refresh')">Retry unchanged command</button></div>
    <p v-if="unavailable" role="status">Access cannot currently be verified. Selection and preparation are paused.</p>
    <p v-if="message" role="status" class="my-4 rounded bg-amber-50 p-4">{{ message }}</p>
    <section class="my-6 flex flex-wrap items-end gap-3 rounded-xl border border-slate-300 bg-slate-50 p-5" aria-label="API source collection">
      <label class="min-w-64">Source connection<select aria-label="Source connection" v-model="refreshForm.endpoint_id" :disabled="blocked"><option value="">Choose an enrolled source</option><option v-for="endpoint in endpoints.items.filter(e => ['vmware', 'openstack', 'ahv'].includes(e.platform))" :key="endpoint.endpoint_id" :value="endpoint.endpoint_id">{{ endpoint.platform }} · {{ endpoint.label }} · {{ endpoint.native_scope }}</option></select></label>
      <button :disabled="blocked || !refreshForm.endpoint_id" @click="refreshApi">Refresh from API</button>
      <button class="secondary" :disabled="blocked" @click="router.get(group ? `${base}/groups/${group.id}` : base)">Refresh findings</button>
      <p class="w-full text-sm text-slate-600">Collection uses existing read permissions and scope. Only complete generations appear below. Additional connections are available through Site inventory.</p>
    </section>
    <div class="my-6 grid gap-4 sm:grid-cols-4" aria-label="Selected resources">
      <div class="rounded-lg bg-slate-900 p-4 text-white"><div class="text-sm">Selected VMs</div><strong class="text-3xl">{{ form.selection.resource_ids.length }}</strong><span class="ml-2 text-sm">of 50 per group</span></div>
      <div class="rounded-lg border p-4"><div class="text-sm text-slate-600">Observed vCPUs</div><strong class="text-2xl">{{ totalCpu }}</strong></div>
      <div class="rounded-lg border p-4"><div class="text-sm text-slate-600">Observed memory</div><strong class="text-2xl">{{ (totalMemory / 1024).toFixed(1) }} GiB</strong></div>
      <div class="rounded-lg border p-4"><div class="text-sm text-slate-600">Profiled disks</div><strong class="text-2xl">{{ (totalDisk / 1024 ** 3).toFixed(1) }} GiB</strong><p class="text-xs">Unknown values excluded; capacity is not reserved.</p></div>
    </div>
    <section class="my-8" aria-label="Discovered source machines">
      <div class="flex flex-wrap items-end gap-4"><label class="grow">Find VMs<input v-model="query" placeholder="Name, source ID, connection, guest OS or power state" /></label><label>Readiness<select v-model="readiness"><option value="all">All discovered VMs</option><option value="review">Ready for owner review</option><option value="held">Held</option></select></label><label>Group list by<select v-model="grouping"><option value="endpoint_label">Source connection</option><option value="guest_id">Guest OS</option><option value="power_state">Power state</option><option value="readiness">Readiness</option></select></label></div>
      <div class="my-4 flex flex-wrap items-center gap-3"><button class="secondary" :disabled="blocked || !visible.length" @click="selectRows(visible)">Select filtered VMs</button><button class="secondary" :disabled="blocked || !form.selection.resource_ids.length" @click="form.selection.resource_ids = []">Clear selection</button><span class="text-sm">{{ visible.length }} matching of {{ rows.length }} loaded. Selections remain when filters change.</span></div>
      <p v-if="!rows.length" class="rounded border p-6">No source machines have been discovered. Select an enrolled source connection and refresh from its API.</p>
      <p v-else-if="!visible.length">No VMs match these filters.</p>
      <section v-for="[label, machines] in sections" :key="label" class="my-5 overflow-hidden rounded-xl border border-slate-300">
        <div class="flex items-center justify-between gap-3 bg-slate-100 p-4"><h2 class="font-semibold">{{ label.replaceAll('_', ' ') }} <span class="font-normal">· {{ machines.length }} VMs</span></h2><button class="secondary" :disabled="blocked" :aria-label="`Select group ${label}`" @click="selectRows(machines)">Select group</button></div>
        <div class="overflow-x-auto"><table class="w-full text-left text-sm"><caption class="sr-only">Discovered VMs in {{ label }}</caption><thead class="bg-slate-50"><tr><th class="p-3">Select</th><th class="p-3">Source VM</th><th class="p-3">Power / guest</th><th class="p-3">Resources</th><th class="p-3">Migration readiness</th><th class="p-3">Review</th></tr></thead><tbody>
          <tr v-for="vm in machines" :key="vm.resource_id" class="border-t align-top" :class="form.selection.resource_ids.includes(vm.resource_id) ? 'bg-teal-50' : ''">
            <td class="p-3"><input v-model="form.selection.resource_ids" type="checkbox" :value="vm.resource_id" :aria-label="`Select ${vm.name} (${vm.native_id})`" :disabled="blocked || (form.selection.resource_ids.length >= 50 && !form.selection.resource_ids.includes(vm.resource_id))" class="w-auto" /></td>
            <td class="p-3"><strong>{{ vm.name }}</strong><p>{{ vm.native_id }} · {{ vm.native_scope }}</p><p class="mt-1 text-xs text-slate-500">Observed {{ observedTime(vm.collected_at) }}</p></td>
            <td class="p-3">{{ vm.power_state ?? 'Unknown' }}<p class="text-xs">{{ vm.guest_id ?? 'Guest profile required' }}</p></td>
            <td class="p-3">{{ vm.cpu ?? '?' }} vCPU · {{ vm.memory_mb === null ? '?' : (vm.memory_mb / 1024).toFixed(1) }} GiB<p class="text-xs">{{ vm.disk_count ?? '?' }} disks</p></td>
            <td class="max-w-sm p-3"><span :class="vm.holds.length || vm.expires_at <= now ? 'text-amber-900' : 'text-teal-900'">{{ vm.holds.length || vm.expires_at <= now ? 'Held' : 'Owner review required' }}</span><ul class="mt-1 text-xs"><li v-if="vm.expires_at <= now">Refresh required</li><li v-for="hold in vm.holds" :key="hold">{{ migrationHold(hold) }}</li></ul></td>
            <td class="p-3"><Link v-if="vm.profile_id && !running" :href="reviewUrl(vm.profile_id)" class="text-teal-800 underline">Review VM</Link><span v-else-if="!vm.profile_id">Collect detailed profile</span></td>
          </tr>
        </tbody></table></div>
      </section>
      <button v-if="cursor" class="secondary" :disabled="blocked" @click="loadMore">{{ loading ? 'Loading…' : 'Load more source VMs' }}</button>
      <p class="mt-3 text-sm text-slate-600">Detailed profiles must be included in the enrolled source scope. Discovery and selection alone do not establish migration compatibility.</p>
    </section>
    <section class="my-8 rounded-xl border border-slate-300 p-5"><h2 class="text-xl font-semibold">{{ group ? 'Edit migration group' : 'Save a migration group' }}</h2><p class="my-3">Use a group for an application, environment or migration wave. Application and environment IDs refer to your catalogue; platform APIs cannot determine ownership.</p>
      <form @submit.prevent="save"><fieldset :disabled="blocked" class="grid gap-4 md:grid-cols-2"><legend class="sr-only">Migration group details</legend>
        <label>Group name<input v-model="form.selection.name" required maxlength="120" placeholder="Finance · production · wave 1" /></label>
        <label>Destination profile<select v-model="form.selection.target_profile_id" required><option value="">Select a current target project</option><option v-for="target in targets" :key="target.id" :value="target.id">{{ target.platform }} · {{ target.native_id }}{{ target.holds.length ? ' · held' : '' }}</option></select></label>
        <label>Catalogue application ID<input v-model="form.selection.application_id" required /></label><label>Catalogue environment ID<input v-model="form.selection.environment_id" required /></label>
        <label>Target disk format<select v-model="form.selection.format"><option v-for="format in ['raw', 'qcow2', 'vmdk']" :key="format" :value="format" :disabled="!selectedTarget?.disk_formats.includes(format)">{{ format.toUpperCase() }}</option></select></label>
        <p v-if="selectedTarget && !selectedTarget.disk_formats.includes(form.selection.format)" role="status">Select a disk format observed for this destination: {{ selectedTarget.disk_formats.join(', ') || 'none available; refresh destination capabilities' }}.</p>
        <div class="self-end"><button type="submit" :disabled="!form.selection.resource_ids.length || !selectedTarget?.disk_formats.includes(form.selection.format)">Save migration group</button></div>
      </fieldset></form>
    </section>
    <section class="my-8"><h2 class="text-xl font-semibold">Saved migration groups</h2><p v-if="!workspace.groups.length" class="my-3">No groups saved yet.</p><div class="my-4 flex flex-wrap gap-3"><Link v-for="saved in workspace.groups" :key="saved.id" :href="`${base}/groups/${saved.id}`" class="action secondary" :class="running ? 'pointer-events-none' : ''">{{ saved.input.name }} · {{ saved.input.members.length }} VMs</Link><Link v-if="group" :href="base" class="action secondary">New group</Link></div></section>
    <section v-if="detail && group" class="my-8 rounded-xl border border-teal-700 p-5" aria-label="Bulk migration preparation">
      <div class="flex flex-wrap items-center justify-between gap-3"><div><h2 class="text-xl font-semibold">{{ group.input.name }}</h2><p class="text-sm">Saved revision {{ group.revision }} · {{ detail.members.length }} VMs</p></div><button :disabled="blocked || dirty" @click="prepareGroup">{{ running ? 'Preparing group…' : 'Prepare group for the selected destination' }}</button></div>
      <p class="my-4">Preparation checks every selected VM independently. Ready members receive exact disk bindings; held members keep their reasons. Starting migrations still requires complete plans, approval and the P08 execution checks.</p>
      <p v-if="dirty" role="status" class="my-3 text-amber-900">Save your changes before preparing this group.</p>
      <table class="w-full text-left text-sm"><thead><tr><th class="p-2">VM</th><th class="p-2">Outcome</th><th class="p-2">Details</th></tr></thead><tbody><tr v-for="member in detail.members" :key="member.candidate.resource_id" class="border-t"><td class="p-2">{{ member.candidate.name }}<p><Link v-if="member.candidate.profile_id && !running" :href="reviewUrl(member.candidate.profile_id)" class="text-teal-800 underline">Review this VM</Link></p></td><td class="p-2">{{ results[member.candidate.resource_id]?.status ?? (member.holds.length ? 'Held' : 'Ready to prepare') }}</td><td class="p-2">{{ results[member.candidate.resource_id]?.reason ?? member.holds.map(migrationHold).join(' ') }}</td></tr></tbody></table>
      <p class="mt-3" role="status">{{ Object.values(results).filter(r => r.status === 'Prepared').length }} prepared · {{ Object.values(results).filter(r => r.status === 'Held').length }} held</p>
      <details v-if="Object.keys(bindings).length" class="mt-4"><summary>Inspect prepared VM bindings</summary><pre class="mt-3 max-h-96 overflow-auto text-xs">{{ JSON.stringify(bindings, null, 2) }}</pre></details>
      <div class="mt-6 border-t pt-5" aria-label="Complete migration plans">
        <h3 class="text-lg font-semibold">Create complete plans</h3>
        <p class="my-3">Find current commissioned plans for each VM, choose rehearsal, cutover or recovery, then create immutable proposals for independent review. Approved plans can be added to a migration campaign.</p>
        <div class="flex flex-wrap gap-3"><button class="secondary" :disabled="blocked || dirty || Object.keys(pending).length > 0" @click="completeGroup('options')">Find plan choices</button><button :disabled="blocked || dirty || !planSelectionReady" @click="completeGroup('compose')">{{ Object.keys(pending).length ? 'Retry plan creation unchanged' : 'Create selected plans' }}</button></div>
        <ul class="my-4 space-y-3"><li v-for="member in detail.members" :key="member.candidate.resource_id" class="flex flex-wrap items-center gap-3">
          <span>{{ member.candidate.name }}</span>
          <Link v-if="plans[member.candidate.resource_id]" :href="planUrl(plans[member.candidate.resource_id])" class="text-teal-800 underline">Review complete plan</Link>
          <select v-else-if="planOptions[member.candidate.resource_id]?.length" v-model="choices[member.candidate.resource_id]" :disabled="blocked || !!pending[member.candidate.resource_id]" :aria-label="`Plan for ${member.candidate.name}`" class="w-auto">
            <option value="">Choose a plan</option><option v-for="option in planOptions[member.candidate.resource_id]" :key="option.recipe_id" :value="option.recipe_id" :disabled="option.expires_at <= now">{{ option.mode.replaceAll('_', ' ') }} · {{ option.method.replaceAll('_', ' ') }} · {{ option.stages }} stages · expires {{ observedTime(option.expires_at) }}</option>
          </select>
        </li></ul>
        <Link :href="`/tenants/${tenantId}/sites/${siteId}/applications/${group.input.application_id}/environments/${group.input.environment_id}/migration-campaigns`" class="text-teal-800 underline">Open migration campaigns</Link>
      </div>
    </section>
  </CatalogueLayout>
</template>
