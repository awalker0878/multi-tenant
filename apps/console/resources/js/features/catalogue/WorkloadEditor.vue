<script setup lang="ts">
import type { Intent, Reference } from './contracts';
import RequirementsEditor from './RequirementsEditor.vue';
const newId = () => crypto.randomUUID();
const value = defineModel<Intent['workloads'][number]>({ required: true });
defineProps<{ index: number; wsds: Reference[]; domains: Reference[]; datasets: Intent['datasets'] }>();
const chooseDomain = (event: Event, options: Reference[]) => {
  const ref = options.find(item => item.id === (event.target as HTMLSelectElement).value);
  if (ref) { value.value.security_domain = { id: ref.id, version: ref.version }; value.value.nics.forEach(nic => { nic.security_domain_id = ref.id; }); }
};
const chooseWsd = (event: Event, options: Reference[]) => { const ref = options.find(item => item.id === (event.target as HTMLSelectElement).value); if (ref) value.value.wsd = { id: ref.id, version: ref.version }; };
</script>
<template>
 <fieldset class="rounded-xl border border-slate-300 p-5">
  <legend class="px-2 text-lg font-semibold">Workload {{ index + 1 }}: {{ value.name || 'New component' }}</legend>
  <div class="grid gap-4 sm:grid-cols-2">
   <label :for="`workload-name-${index}`">Workload name<input :id="`workload-name-${index}`" v-model="value.name" required maxlength="200" /></label>
   <label :for="`workload-role-${index}`">Role<input :id="`workload-role-${index}`" v-model="value.role" required maxlength="64" /></label>
   <label :for="`wsd-${index}`">Workload security domain<select :id="`wsd-${index}`" :value="value.wsd.id" required @change="chooseWsd($event, wsds)"><option value="">Choose a WSD</option><option v-for="ref in wsds.filter(r => !r.retired)" :key="ref.id" :value="ref.id">{{ ref.definition.name }} · version {{ ref.version }}</option><option v-if="value.wsd.id && !wsds.some(r => r.id === value.wsd.id)" :value="value.wsd.id">{{ value.wsd.id }} · version {{ value.wsd.version }}</option></select></label>
   <label :for="`domain-${index}`">Logical security domain<select :id="`domain-${index}`" :value="value.security_domain.id" required @change="chooseDomain($event, domains)"><option value="">Choose a domain</option><option v-for="ref in domains.filter(r => !r.retired)" :key="ref.id" :value="ref.id">{{ ref.definition.name }} · {{ ref.definition.zone }} · version {{ ref.version }}</option><option v-if="value.security_domain.id && !domains.some(r => r.id === value.security_domain.id)" :value="value.security_domain.id">{{ value.security_domain.id }} · version {{ value.security_domain.version }}</option></select></label>
   <label :for="`cpu-${index}`">Virtual CPUs<input :id="`cpu-${index}`" v-model.number="value.compute.vcpus" type="number" min="1" max="4096" required /></label>
   <label :for="`memory-${index}`">Memory (MiB)<input :id="`memory-${index}`" v-model.number="value.compute.memory_mib" type="number" min="128" max="16777216" required /></label>
   <label :for="`architecture-${index}`">Architecture<select :id="`architecture-${index}`" v-model="value.compute.architecture"><option>x86_64</option><option>aarch64</option></select></label>
   <label :for="`os-${index}`">Operating system<input :id="`os-${index}`" v-model="value.guest.os" required maxlength="128" /></label>
   <label :for="`image-${index}`">Requested image<input :id="`image-${index}`" v-model="value.guest.image" required maxlength="512" /></label>
   <label :for="`hardening-${index}`">Guest hardening profile<input :id="`hardening-${index}`" v-model="value.guest.hardening_profile" required maxlength="128" /></label>
   <label :for="`firmware-${index}`">Firmware<select :id="`firmware-${index}`" v-model="value.guest.firmware"><option>uefi</option><option>bios</option></select></label>
   <label class="flex items-center gap-2"><input v-model="value.guest.secure_boot" type="checkbox" />Require secure boot</label>
   <label :for="`failure-group-${index}`">Failure-domain group<input :id="`failure-group-${index}`" v-model="value.failure_domain.group" required maxlength="128" /></label>
   <label :for="`failure-mode-${index}`">Placement relationship<select :id="`failure-mode-${index}`" v-model="value.failure_domain.mode"><option>independent</option><option>affinity</option><option>anti_affinity</option></select></label>
   <label :for="`failure-strength-${index}`">Placement requirement strength<select :id="`failure-strength-${index}`" v-model="value.failure_domain.strength"><option>required</option><option>preferred</option><option>optional</option></select></label>
  </div>
  <h3 class="mt-5 font-semibold">Disks, in attachment order</h3>
  <div v-for="(disk, j) in value.disks" :key="disk.id" class="mt-3 grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-3">
   <label>Disk {{ j + 1 }} size (GiB)<input v-model.number="disk.size_gib" type="number" min="1" max="1048576" required /></label>
   <label>Storage class<input v-model="disk.storage_class" required maxlength="128" /></label>
   <label>Dataset<select v-model="disk.dataset_id"><option :value="null">No dataset</option><option v-for="data in datasets" :key="data.id" :value="data.id">{{ data.name }}</option></select></label>
   <label>Encryption strength<select v-model="disk.encryption"><option>required</option><option>preferred</option><option>optional</option></select></label>
   <label class="flex items-center gap-2"><input v-model="disk.boot" type="checkbox" />Boot disk</label>
   <button type="button" class="secondary" :disabled="value.disks.length === 1" @click="value.disks.splice(j,1); value.disks.forEach((d,k) => d.order=k)">Remove disk {{ j + 1 }}</button>
  </div>
  <button type="button" class="secondary" :disabled="value.disks.length >= 64" @click="value.disks.push({ id: newId(), order: value.disks.length, size_gib: 40, storage_class: 'standard', boot: false, dataset_id: null, encryption: 'required' })">Add disk</button>
  <h3 class="mt-5 font-semibold">Network interfaces, in attachment order</h3>
  <p class="text-sm">Interfaces remain in this workload’s logical security domain. Declare communication between domains as a dependency.</p>
  <div v-for="(nic, j) in value.nics" :key="nic.id" class="mt-3 grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-3">
   <label>Interface {{ j + 1 }} network class<input v-model="nic.network_class" required maxlength="128" /></label>
   <label>Address assignment<select v-model="nic.address_intent"><option>reserved</option><option>dynamic</option><option>static</option></select></label>
   <fieldset><legend>Address families</legend><label><input v-model="nic.address_families" type="checkbox" value="ipv4" />IPv4</label><label><input v-model="nic.address_families" type="checkbox" value="ipv6" />IPv6</label></fieldset>
   <button type="button" class="secondary" @click="value.nics.splice(j,1); value.nics.forEach((n,k) => n.order=k)">Remove interface {{ j + 1 }}</button>
  </div>
  <button type="button" class="secondary" :disabled="value.nics.length >= 16" @click="value.nics.push({ id: newId(), order: value.nics.length, security_domain_id: value.security_domain.id, address_families: ['ipv4'], address_intent: 'reserved', network_class: 'private' })">Add network interface</button>
  <details class="mt-5"><summary class="cursor-pointer font-semibold">Additional workload requirements ({{ value.requirements.length }})</summary><RequirementsEditor v-model="value.requirements" :id="`workload-${index}`" /></details>
 </fieldset>
</template>
