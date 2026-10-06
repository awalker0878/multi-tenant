<script setup lang="ts">
import type { Intent } from './contracts';
const values = defineModel<Intent['requirements']>({ required: true });
defineProps<{ id: string }>();
const changeType = (index: number, event: Event) => {
  const item = values.value[index]; if (!item) return;
  const kind = (event.target as HTMLSelectElement).value;
  item.value = kind === 'boolean' ? item.value === true || item.value === 'true'
    : kind === 'number' ? (Number.isSafeInteger(Number(item.value)) ? Number(item.value) : 0) : String(item.value);
};
</script>
<template>
  <div v-for="(item, index) in values" :key="index" class="grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-2">
    <label :for="`${id}-key-${index}`">Control or capability<input :id="`${id}-key-${index}`" v-model="item.key" required maxlength="128" placeholder="security.encryption" /></label>
    <label :for="`${id}-strength-${index}`">Requirement strength<select :id="`${id}-strength-${index}`" v-model="item.strength"><option>required</option><option>preferred</option><option>optional</option></select></label>
    <label :for="`${id}-type-${index}`">Value type<select :id="`${id}-type-${index}`" :value="typeof item.value" @change="changeType(index, $event)"><option value="string">Text</option><option value="number">Integer</option><option value="boolean">True or false</option></select></label>
    <label :for="`${id}-value-${index}`">Requested value<select v-if="typeof item.value === 'boolean'" :id="`${id}-value-${index}`" v-model="item.value"><option :value="true">True</option><option :value="false">False</option></select><input v-else-if="typeof item.value === 'number'" :id="`${id}-value-${index}`" v-model.number="item.value" type="number" min="-9007199254740991" max="9007199254740991" step="1" required /><input v-else :id="`${id}-value-${index}`" v-model="item.value" required maxlength="2048" /></label>
    <label :for="`${id}-reason-${index}`">Reason<input :id="`${id}-reason-${index}`" v-model="item.reason" required maxlength="500" /></label>
    <button type="button" class="secondary" @click="values.splice(index, 1)">Remove requirement {{ index + 1 }}</button>
  </div>
  <button type="button" class="secondary" :disabled="values.length >= 100" @click="values.push({ key: '', strength: 'required', value: '', reason: '' })">Add requirement</button>
</template>
