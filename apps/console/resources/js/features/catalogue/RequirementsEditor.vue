<script setup lang="ts">
import type { Intent } from './contracts';
const values = defineModel<Intent['requirements']>({ required: true });
defineProps<{ id: string }>();
</script>
<template>
  <div v-for="(item, index) in values" :key="index" class="grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-2">
    <label :for="`${id}-key-${index}`">Control or capability<input :id="`${id}-key-${index}`" v-model="item.key" required maxlength="128" placeholder="security.encryption" /></label>
    <label :for="`${id}-strength-${index}`">Requirement strength<select :id="`${id}-strength-${index}`" v-model="item.strength"><option>required</option><option>preferred</option><option>optional</option></select></label>
    <label :for="`${id}-value-${index}`">Requested value<input :id="`${id}-value-${index}`" v-model="item.value" required maxlength="2048" /></label>
    <label :for="`${id}-reason-${index}`">Reason<input :id="`${id}-reason-${index}`" v-model="item.reason" required maxlength="500" /></label>
    <button type="button" class="secondary" @click="values.splice(index, 1)">Remove requirement {{ index + 1 }}</button>
  </div>
  <button type="button" class="secondary" :disabled="values.length >= 100" @click="values.push({ key: '', strength: 'required', value: '', reason: '' })">Add requirement</button>
</template>
