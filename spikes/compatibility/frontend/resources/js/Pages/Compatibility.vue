<script setup lang="ts">
import { useForm } from '@inertiajs/vue3';
import { computed } from 'vue';

const props = defineProps<{ sampleCount: number; notice: string | null }>();
const message = computed(() => `Compatibility sample: ${props.sampleCount}`);
const form = useForm({ name: '' });

function submit(): void {
  form.post('/compatibility/validate');
}
</script>

<template>
  <main class="mx-auto max-w-xl rounded-lg bg-slate-50 p-6 text-slate-900">
    <h1 class="text-xl font-semibold">{{ message }}</h1>
    <p>Disposable transport probe; no product workflow is implemented.</p>
    <form class="mt-4 space-y-3" @submit.prevent="submit">
      <label class="block" for="sample-name">Sample name</label>
      <input
        id="sample-name"
        v-model="form.name"
        name="name"
        class="rounded border border-slate-500 px-3 py-2"
        :aria-invalid="Boolean(form.errors.name)"
        :aria-describedby="form.errors.name ? 'name-error' : undefined"
      />
      <p v-if="form.errors.name" id="name-error" role="alert">{{ form.errors.name }}</p>
      <button
        type="submit"
        class="block rounded bg-slate-800 px-3 py-2 text-white disabled:opacity-50"
        :disabled="form.processing"
      >
        Submit sample
      </button>
    </form>
    <p v-if="notice" class="mt-4" role="status">{{ notice }}</p>
  </main>
</template>
