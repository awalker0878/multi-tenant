<script setup lang="ts">
import { computed, nextTick } from 'vue';
import { Link, router, useForm } from '@inertiajs/vue3';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';
import type { Endpoint, EndpointList, Health, Policy } from '../../features/inventory/contracts';
import { observedTime, useInventoryAccess } from '../../features/inventory/useAccess';
const props = defineProps<{ tenantId: string; siteId: string; endpoints: EndpointList; policies: Policy[]; health: Health; canAdminister: boolean; canDiscover: boolean; notice: string | null }>();
const base = `/tenants/${props.tenantId}/inventory/sites/${props.siteId}`;
const { now, unavailable } = useInventoryAccess(base + '/status');
const form = useForm({ operation: 'enrollEndpoint', command_key: crypto.randomUUID(), endpoint_id: null as string | null, revision: null as number | null, policy_id: '', label: '' });
const errors = computed(() => form.errors as Record<string, string>);
const uncertain = computed(() => errors.value.inventory_status === '503');
const focusError = async () => { await nextTick(); document.getElementById('inventory-errors')?.focus(); };
const submit = () => form.post(base + '/commands', { preserveState: true, onError: () => { void focusError(); }, onSuccess: () => { form.reset(); form.command_key = crypto.randomUUID(); } });
const act = (operation: string, endpoint: Endpoint) => {
  if (uncertain.value) return;
  form.clearErrors(); form.operation = operation; form.endpoint_id = endpoint.endpoint_id;
  form.revision = endpoint.revision; form.command_key = crypto.randomUUID(); submit();
};
const enroll = () => { if (!uncertain.value) { form.operation = 'enrollEndpoint'; form.endpoint_id = null; form.revision = null; } submit(); };
const refresh = () => router.get(base);
const state = (endpoint: Endpoint) => endpoint.expires_at !== null && endpoint.expires_at <= now.value ? 'expired' : endpoint.reason ?? 'fresh within approved scope';
</script>
<template>
  <CatalogueLayout title="Site inventory" :tenant-id="tenantId">
    <Link :href="`/tenants/${tenantId}/inventory`" class="text-teal-800 underline">All inventory sites</Link>
    <p class="mt-3 break-all text-sm text-slate-600">Site {{ siteId }}</p>
    <p class="mt-4 max-w-3xl">Read-only enrollment allows approved discovery. Native changes require separate commissioning. Observed capacity remains unreserved.</p>
    <p v-if="notice" role="status" class="mt-4 rounded-lg bg-teal-50 p-4">{{ notice }}</p>
    <p v-if="unavailable" role="status" class="mt-4 rounded-lg bg-amber-50 p-4">Current access could not be checked. Commands are paused; displayed observations retain their expiry.</p>
    <div v-if="Object.keys(errors).length" id="inventory-errors" role="alert" tabindex="-1" class="my-4">
      <p>{{ errors.command ?? Object.values(errors)[0] }}</p>
      <button v-if="uncertain" type="button" :disabled="form.processing || unavailable" @click="submit">Retry unchanged command</button>
    </div>
    <button type="button" class="secondary" :disabled="form.processing || uncertain" @click="refresh">Refresh site status</button>
    <dl class="my-6 flex flex-wrap gap-6" aria-label="Collection queue">
      <div v-for="row in health.items" :key="row.status"><dt class="text-sm capitalize text-slate-600">{{ row.status }}</dt><dd class="text-2xl font-semibold">{{ row.count }}</dd></div>
    </dl>
    <section class="grid gap-5 lg:grid-cols-2" aria-label="Enrolled endpoints">
      <article v-for="endpoint in endpoints.items" :key="endpoint.endpoint_id" class="rounded-xl border border-slate-300 bg-white p-5">
        <div class="flex flex-wrap items-start justify-between gap-3"><h2 class="text-xl font-semibold">{{ endpoint.label }}</h2><span class="rounded-full bg-slate-100 px-3 py-1 text-sm">{{ endpoint.platform }}</span></div>
        <p class="mt-3 font-medium" :class="state(endpoint) === 'fresh within approved scope' ? 'text-teal-800' : 'text-amber-900'">{{ state(endpoint).replaceAll('_', ' ') }}</p>
        <dl class="mt-4 grid gap-2 text-sm sm:grid-cols-[8rem_1fr]"><dt>Native scope</dt><dd class="break-all">{{ endpoint.native_scope }}</dd><dt>Freshness expires</dt><dd>{{ observedTime(endpoint.expires_at) }}</dd><dt>Coverage reference</dt><dd class="break-all">{{ endpoint.coverage_reference ?? 'Not established' }}</dd><dt>Write readiness</dt><dd>Not commissioned</dd></dl>
        <div class="mt-4 flex flex-wrap gap-2">
          <Link v-if="endpoint.generation_id" :href="`${base}/generations/${endpoint.generation_id}`" class="action secondary">Browse observations</Link>
          <button v-if="canDiscover" type="button" :disabled="form.processing || uncertain || unavailable" @click="act('requestDiscovery', endpoint)">Request discovery</button>
          <button v-if="canAdminister" type="button" class="secondary" :disabled="form.processing || uncertain || unavailable" @click="act('renewEndpoint', endpoint)">Renew enrollment</button>
          <button v-if="canAdminister" type="button" class="secondary" :disabled="form.processing || uncertain || unavailable" @click="act('revokeEndpoint', endpoint)">Revoke collector</button>
        </div>
        <details class="mt-5"><summary class="cursor-pointer font-medium">Installed declarations and capability gaps</summary>
          <p class="my-3 text-sm">These declarations identify the intended installation. Capability qualification remains unassessed.</p>
          <dl class="space-y-3"><div v-for="(dimension, name) in endpoint.profile.dimensions" :key="name"><dt class="font-medium">{{ name.replaceAll('_', ' ') }}</dt><dd class="text-sm">{{ dimension.state }} · {{ dimension.reason.replaceAll('_', ' ') }}<pre v-if="Object.keys(dimension.facts).length" class="mt-2 whitespace-pre-wrap break-all rounded bg-slate-50 p-3">{{ JSON.stringify(dimension.facts, null, 2) }}</pre></dd></div></dl>
        </details>
      </article>
    </section>
    <p v-if="!endpoints.items.length" class="my-6">No endpoints are enrolled on this page.</p>
    <Link v-if="endpoints.next_cursor" :href="`${base}?cursor=${endpoints.next_cursor}`" class="action secondary">Next endpoints</Link>
    <form v-if="canAdminister" class="mt-9 max-w-xl rounded-xl border border-slate-300 bg-white p-5" @submit.prevent="enroll">
      <h2 class="text-xl font-semibold">Enroll an approved endpoint</h2>
      <p v-if="!policies.length" class="mt-3">No current site policy names you as its owner. The site authority must provide the approved trust and read scope.</p>
      <fieldset :disabled="form.processing || uncertain || unavailable || !policies.length" class="mt-5 space-y-4">
        <label for="inventory-policy">Approved scope<select id="inventory-policy" v-model="form.policy_id" required><option value="">Choose a scope</option><option v-for="policy in policies" :key="policy.policy_id" :value="policy.policy_id">{{ policy.platform }} · {{ policy.native_scope }}</option></select></label>
        <label for="inventory-label">Endpoint label<input id="inventory-label" v-model="form.label" required maxlength="120" /></label>
        <button type="submit">Enroll for read-only discovery</button>
      </fieldset>
    </form>
  </CatalogueLayout>
</template>
