<script setup lang="ts">
import { ref } from 'vue';
import { Link, router } from '@inertiajs/vue3';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';
import type { SiteList } from '../../features/inventory/contracts';
const props = defineProps<{ tenantId: string; sites: SiteList }>();
const site = ref('');
const open = () => { if (/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(site.value)) router.get(`/tenants/${props.tenantId}/inventory/sites/${site.value}`); };
</script>
<template>
  <CatalogueLayout title="Observed inventory" :tenant-id="tenantId">
    <p class="max-w-3xl text-slate-700">Browse resources visible within your approved site scopes. Discovery records observations; capacity reservations and resource ownership are assessed separately.</p>
    <ul class="my-6 grid gap-4 sm:grid-cols-2">
      <li v-for="item in sites.items" :key="item.site_id" class="rounded-xl border border-slate-300 bg-white p-5">
        <Link :href="`/tenants/${tenantId}/inventory/sites/${item.site_id}`" class="break-all font-semibold text-teal-800 underline">Site {{ item.site_id }}</Link>
      </li>
    </ul>
    <p v-if="!sites.items.length" class="my-6">No enrolled sites on this page. A site owner can open an approved site below to enroll its endpoint.</p>
    <Link v-if="sites.next_cursor" :href="`/tenants/${tenantId}/inventory?cursor=${sites.next_cursor}`" class="action secondary">Next sites</Link>
    <form class="mt-8 max-w-xl" @submit.prevent="open">
      <label for="inventory-site">Approved site ID<input id="inventory-site" v-model="site" required maxlength="36" pattern="[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}" /></label>
      <button type="submit">Open site</button>
    </form>
  </CatalogueLayout>
</template>
