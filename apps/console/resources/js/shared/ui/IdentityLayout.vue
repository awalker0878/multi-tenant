<script setup lang="ts">
import { Head } from '@inertiajs/vue3';

defineProps<{ title: string; description: string }>();
</script>

<template>
  <Head :title="`${title} | Workload Mobility`" />
  <main class="mx-auto flex min-h-screen max-w-xl flex-col justify-center px-6 py-16">
    <a href="/" class="mb-8 text-sm font-semibold uppercase tracking-widest text-teal-800">Workload Mobility</a>
    <section class="identity-card rounded-2xl border border-slate-300 bg-white p-6 shadow-sm sm:p-9" aria-labelledby="identity-heading">
      <h1 id="identity-heading" class="text-3xl font-semibold tracking-tight text-slate-950">{{ title }}</h1>
      <p class="mt-3 leading-7 text-slate-700">{{ description }}</p>
      <slot />
    </section>
  </main>
</template>

<style scoped>
.identity-card :deep(form) { margin-top: 1.5rem; }
.identity-card :deep(label) { display: block; margin-top: 1rem; font-weight: 600; color: #0f172a; }
.identity-card :deep(input) { width: 100%; margin-top: .5rem; border: 1px solid #64748b; border-radius: .5rem; padding: .7rem; background: white; }
.identity-card :deep(input:focus-visible), .identity-card :deep(button:focus-visible), .identity-card :deep(a:focus-visible) { outline: 3px solid #0f766e; outline-offset: 3px; }
.identity-card :deep(button) { margin-top: 1.5rem; min-height: 44px; border-radius: .5rem; background: #115e59; color: white; font-weight: 600; padding: .7rem 1.1rem; cursor: pointer; }
.identity-card :deep(button:disabled) { opacity: .65; cursor: wait; }
.identity-card :deep([role="alert"]) { margin-top: .4rem; color: #9f1239; font-size: .9rem; }
</style>
