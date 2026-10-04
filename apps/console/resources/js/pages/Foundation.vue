<script setup lang="ts">
import { Head } from '@inertiajs/vue3';

defineProps<{
  productName: string;
  implementationState: 'foundation';
}>();
</script>

<template>
  <Head title="Workload Mobility | Foundation" />
  <main class="mx-auto flex min-h-screen max-w-4xl flex-col justify-center px-6 py-16 sm:px-10">
    <p class="mb-5 text-sm font-semibold uppercase tracking-widest text-teal-800">Workload Mobility</p>
    <h1 class="max-w-3xl text-4xl font-semibold leading-tight tracking-tight text-slate-950 sm:text-5xl">
      {{ productName }}
    </h1>
    <p class="mt-6 max-w-2xl text-lg leading-8 text-slate-700">
      Provision and move workloads across VMware, Nutanix and OpenStack,
      with tenant security policy and evidence following each workload.
    </p>
    <section class="mt-12 rounded-2xl border border-slate-300 bg-white p-6 sm:p-8" aria-labelledby="status-heading">
      <h2 id="status-heading" class="text-xl font-semibold text-slate-950">Console foundation</h2>
      <p class="mt-3 max-w-2xl leading-7 text-slate-700">
        This application is being built. Sign-in, tenant access and workload operations
        are not available yet.
      </p>
      <p class="mt-5 text-sm font-medium text-teal-800">Development stage: {{ implementationState }}</p>
    </section>
  </main>
</template>
