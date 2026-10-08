<script setup lang="ts">
import { Head, Link, usePage } from '@inertiajs/vue3';
import { computed, nextTick, onMounted, ref } from 'vue';
import BrandMark from './BrandMark.vue';
const props = defineProps<{ title: string; tenantId: string }>();
const page = usePage();
const menuOpen = ref(false);
const nav = computed(() => [
  { label: 'Your tenants', href: '/account', short: '01' },
  { label: 'Applications', href: `/tenants/${props.tenantId}/applications`, short: '02' },
  { label: 'Environments and domains', href: `/tenants/${props.tenantId}/catalogue-references`, short: '03' },
  { label: 'Observed inventory', href: `/tenants/${props.tenantId}/inventory`, short: '04' },
  { label: 'Tenant settings', href: `/tenants/${props.tenantId}`, short: '05' },
]);
const active = (href: string) => href.endsWith(props.tenantId) ? page.url.split('?')[0] === href : page.url.split('?')[0].startsWith(href);
onMounted(async () => { await nextTick(); document.getElementById('catalogue-heading')?.focus(); });
</script>
<template>
  <Head :title="`${title} | Workload Mobility`" />
  <a class="skip-link" href="#workspace-main">Skip to workspace</a>
  <div class="console-shell">
    <aside class="console-sidebar">
      <Link href="/account" class="sidebar-brand" aria-label="Workload Mobility home"><BrandMark /></Link>
      <button class="mobile-menu" type="button" :aria-expanded="menuOpen" aria-controls="workspace-navigation" @click="menuOpen = !menuOpen">{{ menuOpen ? 'Close navigation' : 'Workspace navigation' }}</button>
      <nav id="workspace-navigation" aria-label="Workspace navigation" :class="{ 'is-open': menuOpen }">
        <p class="nav-caption">WORKSPACE</p>
        <Link v-for="item in nav" :key="item.href" :href="item.href" :aria-current="active(item.href) ? 'page' : undefined" class="nav-item"><span aria-hidden="true">{{ item.short }}</span>{{ item.label }}</Link>
      </nav>
      <div class="sidebar-foot" :class="{ 'is-open': menuOpen }"><p>Tenant workspace</p><code>{{ tenantId.slice(0, 8) }}</code><Link href="/logout" method="post" as="button" class="signout">Sign out</Link></div>
    </aside>
    <div class="console-content">
      <header class="console-topbar"><span>OPERATIONS CONSOLE</span><span class="context-badge">Tenant scoped</span></header>
      <main id="workspace-main" class="catalogue" tabindex="-1">
        <div class="page-heading"><p class="eyebrow">Workload Mobility / Workspace</p><h1 id="catalogue-heading" tabindex="-1">{{ title }}</h1></div>
        <slot />
      </main>
      <footer class="console-footer">Workload Mobility<span>Provision · Migrate · Verify</span></footer>
    </div>
  </div>
</template>
