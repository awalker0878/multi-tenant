<script setup lang="ts">
import { computed, nextTick, ref } from 'vue';
import { Link, useForm } from '@inertiajs/vue3';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';
import type { Resource, ResourceList } from '../../features/inventory/contracts';
import { observedTime, useInventoryAccess } from '../../features/inventory/useAccess';
const props = defineProps<{ tenantId: string; siteId: string; resources: ResourceList; canMatch: boolean; notice: string | null }>();
const base = `/tenants/${props.tenantId}/inventory/sites/${props.siteId}`;
const { now, unavailable } = useInventoryAccess(base + '/status');
const search = ref('');
const visible = computed(() => props.resources.items.filter(row => `${row.observation.name} ${row.observation.native_id} ${row.observation.kind}`.toLowerCase().includes(search.value.toLowerCase())));
const holds = (row: Resource) => [...new Set([...row.holds, ...(row.expires_at <= now.value ? ['expired'] : [])])];
const form = useForm({ operation: 'proposeMatch', command_key: crypto.randomUUID(), endpoint_id: props.resources.endpoint_id, resource_id: '', application_id: '', intent_revision: '', environment: '', generation_id: props.resources.generation_id });
const errors = computed(() => form.errors as Record<string, string>);
const uncertain = computed(() => errors.value.inventory_status === '503');
const selected = computed(() => props.resources.items.find(r => r.resource_id === form.resource_id));
const choose = (row: Resource) => { if (uncertain.value) return; form.resource_id = row.resource_id; form.command_key = crypto.randomUUID(); form.clearErrors(); void nextTick(() => document.getElementById('match-application')?.focus()); };
const submit = () => form.post(base + '/commands', { preserveState: true, onSuccess: () => { form.reset(); form.command_key = crypto.randomUUID(); }, onError: () => { void nextTick(() => document.getElementById('inventory-errors')?.focus()); } });
</script>
<template>
  <CatalogueLayout title="Observed resources" :tenant-id="tenantId">
    <Link :href="base" class="text-teal-800 underline">Site health and discovery</Link>
    <p class="mt-4 break-all text-sm text-slate-600">Generation {{ resources.generation_id }} · {{ resources.completion }}</p>
    <p class="mt-3">These resources remain observation-only. A matching proposal does not grant ownership or reserve capacity.</p>
    <p v-if="resources.completion !== 'complete'" role="status" class="my-5 rounded border border-amber-700 bg-amber-50 p-4">This scan is incomplete. {{ resources.reason?.replaceAll('_', ' ') ?? 'Collection is still running.' }} An empty page does not establish an empty site.</p>
    <p v-if="notice" role="status" class="my-4">{{ notice }}</p>
    <p v-if="unavailable" role="status" class="my-4">Current access could not be checked. Matching is paused.</p>
    <label for="inventory-search" class="my-5 max-w-xl">Filter this page<input id="inventory-search" v-model="search" maxlength="120" type="search" /></label>
    <div class="overflow-x-auto"><table class="w-full"><caption class="sr-only">Observed resources in this fixed generation</caption><thead><tr><th scope="col">Resource</th><th scope="col">Observed / expires</th><th scope="col">Eligibility holds</th><th scope="col">Review</th></tr></thead>
      <tbody><tr v-for="row in visible" :key="row.resource_id"><th scope="row" class="font-normal"><strong>{{ row.observation.name }}</strong><p class="mt-1 text-sm">{{ row.observation.kind }} · {{ row.observation.native_id }}</p><dl class="mt-2 text-xs"><div v-for="(value, key) in row.observation.facts" :key="key"><dt class="inline">{{ key }}: </dt><dd class="inline">{{ value }}</dd></div></dl></th>
        <td class="text-sm">{{ observedTime(row.collected_at) }}<p class="mt-2">Expires {{ observedTime(row.expires_at) }}</p></td>
        <td><ul v-if="holds(row).length" class="text-amber-900"><li v-for="hold in holds(row)" :key="hold">{{ hold.replaceAll('_', ' ') }}</li></ul><p v-else>None from this observation</p><p class="mt-2 text-sm">{{ row.proposed_matches }} proposed matches · unreserved</p></td>
        <td><button v-if="canMatch" type="button" class="secondary" :disabled="form.processing || uncertain || unavailable || holds(row).length > 0" @click="choose(row)">Propose application match</button><p v-else class="text-sm">Read access</p></td></tr></tbody>
    </table></div>
    <p v-if="!visible.length" class="my-5">No resources match this page filter.</p>
    <Link v-if="resources.next_cursor" :href="`${base}/generations/${resources.generation_id}?cursor=${resources.next_cursor}`" class="action secondary">Next resource page</Link>
    <div v-if="Object.keys(errors).length" id="inventory-errors" role="alert" tabindex="-1" class="my-5"><p>{{ errors.command ?? Object.values(errors)[0] }}</p><button v-if="uncertain" type="button" :disabled="form.processing || unavailable" @click="submit">Retry unchanged proposal</button></div>
    <form v-if="canMatch && selected" class="mt-8 max-w-xl rounded-xl border border-slate-300 bg-white p-5" @submit.prevent="submit">
      <h2 class="text-xl font-semibold">Propose {{ selected.observation.name }}</h2>
      <p class="my-3 text-sm">Use the immutable revision shown in the application catalogue. Its current access is checked before the proposal is recorded. Lifecycle ownership requires a separate review.</p>
      <fieldset :disabled="form.processing || uncertain || unavailable || holds(selected).length > 0" class="space-y-4">
        <label for="match-application">Application ID<input id="match-application" v-model="form.application_id" required maxlength="36" /></label>
        <label for="match-revision">Intent revision ID<input id="match-revision" v-model="form.intent_revision" required maxlength="36" /></label>
        <label for="match-environment">Environment ID<input id="match-environment" v-model="form.environment" required maxlength="36" /></label>
        <button type="submit">Record matching proposal</button>
      </fieldset>
    </form>
  </CatalogueLayout>
</template>
