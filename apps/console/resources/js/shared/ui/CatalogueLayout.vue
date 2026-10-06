<script setup lang="ts">
import { Head, Link } from '@inertiajs/vue3';
import { nextTick, onMounted } from 'vue';
defineProps<{ title: string; tenantId: string }>();
onMounted(async () => { await nextTick(); document.getElementById('catalogue-heading')?.focus(); });
</script>
<template>
 <Head :title="`${title} | Workload Mobility`" />
 <main class="catalogue mx-auto min-h-screen max-w-6xl px-5 py-10 text-slate-900">
  <nav aria-label="Catalogue navigation" class="mb-8 flex flex-wrap gap-5 text-sm font-semibold text-teal-800">
   <Link href="/account">Your tenants</Link><Link :href="`/tenants/${tenantId}`">Tenant settings</Link><Link :href="`/tenants/${tenantId}/applications`">Applications</Link><Link :href="`/tenants/${tenantId}/catalogue-references`">Environments and domains</Link>
   <Link href="/logout" method="post" as="button" class="ml-auto">Sign out</Link>
  </nav>
  <h1 id="catalogue-heading" tabindex="-1" class="mb-7 text-3xl font-semibold tracking-tight">{{ title }}</h1><slot />
 </main>
</template>
<style scoped>
.catalogue :deep(label) { display: block; font-weight: 600; font-size: .9rem; }
.catalogue :deep(input:not([type=checkbox])), .catalogue :deep(select), .catalogue :deep(textarea) { display: block; width: 100%; margin-top: .4rem; min-height: 44px; border: 1px solid #64748b; border-radius: .45rem; padding: .6rem; background: white; font-weight: 400; }
.catalogue :deep(input[type=checkbox]) { width: 20px; height: 20px; vertical-align: middle; margin-right: .5rem; }
.catalogue :deep(button), .catalogue :deep(.action) { display: inline-block; margin-top: .65rem; min-height: 44px; border-radius: .45rem; padding: .6rem 1rem; background: #115e59; color: white; font-weight: 600; cursor: pointer; }
.catalogue :deep(.secondary) { background: white; border: 1px solid #64748b; color: #134e4a; }
.catalogue :deep(:focus-visible) { outline: 3px solid #0f766e; outline-offset: 3px; }
.catalogue :deep(button:disabled) { cursor: not-allowed; opacity: .55; }
.catalogue :deep([role=alert]) { padding: 1rem; border: 1px solid #be123c; border-radius: .5rem; background: #fff1f2; color: #881337; }
.catalogue :deep(th), .catalogue :deep(td) { padding: .8rem; text-align: left; vertical-align: top; border-bottom: 1px solid #cbd5e1; overflow-wrap: anywhere; }
.catalogue :deep(nav button) { margin: 0; background: transparent; color: #115e59; padding: 0; min-height: 24px; }
</style>
