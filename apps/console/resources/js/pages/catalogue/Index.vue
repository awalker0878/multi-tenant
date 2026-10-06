<script setup lang="ts">
import { Link } from '@inertiajs/vue3';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';
import type { ApplicationSummary } from '../../features/catalogue/contracts';
defineProps<{ tenantId: string; environment: string | null; applications: ApplicationSummary[]; nextCursor: string | null; canCreate: boolean; notice: string | null }>();
</script>
<template>
 <CatalogueLayout title="Application catalogue" :tenant-id="tenantId">
  <p class="max-w-2xl text-slate-600">Define the workloads, data, dependencies and requirements your application needs. Every publication keeps an immutable revision for assessment and review.</p>
  <p v-if="notice" role="status" class="mt-4">{{ notice }}</p>
  <Link v-if="canCreate" class="action" :href="`/tenants/${tenantId}/applications/create${environment ? '?environment=' + environment : ''}`">Create or import application</Link>
  <p v-if="!applications.length" class="mt-8 rounded-lg border border-slate-200 bg-white p-6">There are no applications on this page.</p>
  <ul v-else class="mt-7 grid gap-4 sm:grid-cols-2"><li v-for="app in applications" :key="app.id" class="rounded-xl border border-slate-300 bg-white p-6"><h2 class="text-xl font-semibold"><Link :href="`/tenants/${tenantId}/applications/${app.id}${environment ? '?environment=' + environment : ''}`" class="text-teal-800 underline">{{ app.name }}</Link></h2><p class="mt-2 break-all text-xs text-slate-600">Application {{ app.id }}</p></li></ul>
  <Link v-if="nextCursor" class="action secondary" :href="`/tenants/${tenantId}/applications?cursor=${encodeURIComponent(nextCursor)}${environment ? '&environment=' + environment : ''}`">Next applications</Link>
 </CatalogueLayout>
</template>
