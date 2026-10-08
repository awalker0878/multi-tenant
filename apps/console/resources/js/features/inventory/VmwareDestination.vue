<script setup lang="ts">
import { computed } from 'vue';
import type { VmwareDestinationSelection, VmwareTargetCapabilityProfile } from './contracts';
const props = defineProps<{ profile: VmwareTargetCapabilityProfile; sourceGuestId: string | null }>();
const model = defineModel<VmwareDestinationSelection>({ required: true });
const catalog = computed(() => props.profile.guest_options_by_host?.find(item => item.host === model.value.host_id));
function hostChanged() { model.value.guest_id = ''; model.value.hardware_version = ''; }
</script>
<template>
  <fieldset class="space-y-4 rounded border border-slate-300 p-4">
    <legend class="text-xl font-semibold">VMware destination mapping</legend>
    <p>Datacenter {{ profile.project_id }} · vCenter {{ profile.vcenter_uuid }} · API {{ profile.api_version }}</p>
    <p>All disks are imported into a powered-off VM with disconnected quarantine NICs. Select guest compatibility from the approved preparation profile.</p>
    <div class="grid gap-4 md:grid-cols-2">
      <label>VM folder<select v-model="model.folder_id" required><option value="">Select folder</option><option v-for="r in profile.folders" :key="r.folder" :value="r.folder">{{ r.name }}</option></select></label>
      <label>Resource pool<select v-model="model.resource_pool_id" required><option value="">Select resource pool</option><option v-for="r in profile.resource_pools" :key="r.resource_pool" :value="r.resource_pool">{{ r.name }}</option></select></label>
      <label>Host<select v-model="model.host_id" required @change="hostChanged"><option value="">Select host</option><option v-for="r in profile.hosts.filter(h => profile.guest_options_by_host?.some(c => c.host === h.host))" :key="r.host" :value="r.host">{{ r.name }}</option></select></label>
      <label>Datastore<select v-model="model.datastore_id" required><option value="">Select datastore</option><option v-for="r in profile.datastores" :key="r.datastore" :value="r.datastore">{{ r.name }}</option></select></label>
      <label v-if="sourceGuestId">Guest compatibility ID<select v-model="model.guest_id" required><option value="">Select observed guest OS</option><option v-for="id in (catalog?.guest_ids ?? [])" :key="id" :value="id">{{ id }}</option></select></label>
      <label v-if="sourceGuestId">Hardware compatibility<select v-model="model.hardware_version" required><option value="">Select observed hardware version</option><option v-for="v in (catalog?.hardware_versions ?? [])" :key="v" :value="v">{{ v }}</option></select></label>
      <p v-if="!sourceGuestId" role="alert">Source guest OS is not known; no destination compatibility selection is available.</p>
      <p v-else-if="!catalog" role="alert">The destination API did not return guest and hardware compatibility for this host. No manual override is accepted.</p>
    </div>
    <p>Firmware: {{ model.firmware }}. Changing firmware requires its own qualified preparation procedure.</p>
    <label v-for="d in model.disks" :key="d.source_key">Source disk {{ d.source_key }} → disk order<input v-model.number="d.index" type="number" min="0" :max="model.disks.length - 1" required /></label>
    <div v-for="nic in model.nics" :key="nic.source_key" class="grid gap-4 md:grid-cols-2">
      <label>NIC {{ nic.source_key }} quarantine network<select v-model="nic.quarantine_network_id" required><option value="">Select quarantine network</option><option v-for="r in profile.networks" :key="r.network" :value="r.network">{{ r.name }}</option></select></label>
      <label>NIC {{ nic.source_key }} production network<select v-model="nic.production_network_id" required><option value="">Select production network</option><option v-for="r in profile.networks.filter(n => n.network !== nic.quarantine_network_id)" :key="r.network" :value="r.network">{{ r.name }}</option></select></label>
    </div>
  </fieldset>
</template>
