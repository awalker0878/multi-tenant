<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{ sampleCount: number }>();
const message = computed(() => `Compatibility sample: ${props.sampleCount}`);
</script>

<template>
  <main class="mx-auto max-w-xl rounded-lg bg-slate-50 p-6 text-slate-900">
    <h1 class="text-xl font-semibold">{{ message }}</h1>
    <p>Disposable build probe; no product workflow is implemented.</p>
  </main>
</template>
