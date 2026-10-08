<script setup lang="ts">
import type { VmwareDestinationSelection, VmwareTargetCapabilityProfile } from './contracts';
defineProps<{ profile: VmwareTargetCapabilityProfile }>();
const model = defineModel<VmwareDestinationSelection>({ required: true });
</script>
<template>
  <fieldset class="space-y-4 rounded border border-slate-300 p-4">
    <legend class="text-xl font-semibold">VMware destination mapping</legend>
    <p>Datacenter {{ profile.project_id }} · vCenter {{ profile.vcenter_uuid }} · API {{ profile.api_version }}</p>
    <p>All disks are imported into a powered-off VM with disconnected quarantine NICs. Select guest compatibility from the approved preparation profile.</p>
    <div class="grid gap-4 md:grid-cols-2">
      <label>VM folder<select v-model="model.folder_id" required><option value="">Select folder</option><option v-for="r in profile.folders" :key="r.folder" :value="r.folder">{{ r.name }}</option></select></label>
      <label>Resource pool<select v-model="model.resource_pool_id" required><option value="">Select resource pool</option><option v-for="r in profile.resource_pools" :key="r.resource_pool" :value="r.resource_pool">{{ r.name }}</option></select></label>
      <label>Host<select v-model="model.host_id" required><option value="">Select host</option><option v-for="r in profile.hosts" :key="r.host" :value="r.host">{{ r.name }}</option></select></label>
      <label>Datastore<select v-model="model.datastore_id" required><option value="">Select datastore</option><option v-for="r in profile.datastores" :key="r.datastore" :value="r.datastore">{{ r.name }}</option></select></label>
      <label>Guest compatibility ID<input v-model="model.guest_id" required maxlength="85" placeholder="rhel9_64Guest" /></label>
      <label>Hardware compatibility<input v-model="model.hardware_version" required pattern="vmx-[0-9]{2}" placeholder="vmx-21" /></label>
    </div>
    <p>Firmware: {{ model.firmware }}. Changing firmware requires its own qualified preparation procedure.</p>
    <label v-for="d in model.disks" :key="d.source_key">Source disk {{ d.source_key }} → disk order<input v-model.number="d.index" type="number" min="0" :max="model.disks.length - 1" required /></label>
    <div v-for="nic in model.nics" :key="nic.source_key" class="grid gap-4 md:grid-cols-2">
      <label>NIC {{ nic.source_key }} quarantine network<select v-model="nic.quarantine_network_id" required><option value="">Select quarantine network</option><option v-for="r in profile.networks" :key="r.network" :value="r.network">{{ r.name }}</option></select></label>
      <label>NIC {{ nic.source_key }} production network<select v-model="nic.production_network_id" required><option value="">Select production network</option><option v-for="r in profile.networks.filter(n => n.network !== nic.quarantine_network_id)" :key="r.network" :value="r.network">{{ r.name }}</option></select></label>
    </div>
  </fieldset>
</template>
