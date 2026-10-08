<script setup lang="ts">
import { computed } from 'vue';
import type { AhvDestinationSelection, AhvTargetCapabilityProfile } from './contracts';
const props = defineProps<{ profile: AhvTargetCapabilityProfile; sourceFirmware: string | null }>();
const model = defineModel<AhvDestinationSelection>({ required: true });
const subnets = computed(() => props.profile.subnets.filter(s => s.vpcReference === model.value.vpc_id));
function changeVpc() {
  for (const nic of model.value.nics) { nic.quarantine_subnet_id = ''; nic.production_subnet_id = ''; }
}
</script>
<template>
  <fieldset class="space-y-4 rounded border border-slate-300 p-4">
    <legend class="text-xl font-semibold">AHV destination mapping</legend>
    <p>Project {{ profile.project_id }} · Cluster {{ profile.cluster_name || profile.cluster_id }} · Prism Central {{ profile.prism_central_id }}</p>
    <p>Cold export preserves the selected firmware, with raw disks on SCSI and VirtIO NICs. Guest preparation must match the approved operating system and driver profile. The imported VM starts powered off with disconnected NICs on quarantine networks. Native qualification and activation approval are required separately.</p>
    <p v-if="sourceFirmware !== model.firmware" role="alert">Source and destination firmware must match.</p>
    <div class="grid gap-4 md:grid-cols-2">
      <label>Storage container<select v-model="model.storage_container_id" required><option value="">Select observed storage</option><option v-for="row in profile.storage_containers" :key="row.extId" :value="row.extId">{{ row.name || row.extId }}</option></select></label>
      <label>Network scope<select v-model="model.vpc_id" @change="changeVpc"><option :value="null">Cluster VLAN networks</option><option v-for="row in profile.vpcs" :key="row.extId" :value="row.extId">{{ row.name || row.extId }}</option></select></label>
    </div>
    <fieldset><legend>Observed categories</legend><label v-for="row in profile.categories" :key="row.extId" class="mr-4 inline-flex gap-2"><input v-model="model.category_ids" type="checkbox" :value="row.extId" class="w-auto" />{{ row.key }}: {{ row.value }}</label></fieldset>
    <fieldset><legend>Security policies to validate</legend><label v-for="row in profile.policies" :key="row.extId" class="mr-4 inline-flex gap-2"><input v-model="model.policy_ids" type="checkbox" :value="row.extId" class="w-auto" />{{ row.name || row.extId }} · {{ row.state }}</label></fieldset>
    <p>Category membership and policy presence do not prove isolation. Qualification must test both allowed and denied traffic.</p>
    <div v-for="disk in model.disks" :key="disk.source_key"><label>Source disk {{ disk.source_key }} → SCSI slot<input v-model.number="disk.index" type="number" min="0" :max="model.disks.length - 1" required /></label></div>
    <div v-for="nic in model.nics" :key="nic.source_key" class="grid gap-4 md:grid-cols-2">
      <label>NIC {{ nic.source_key }} quarantine subnet<select v-model="nic.quarantine_subnet_id" required><option value="">Select quarantine network</option><option v-for="row in subnets" :key="row.extId" :value="row.extId">{{ row.name || row.extId }}</option></select></label>
      <label>NIC {{ nic.source_key }} production subnet<select v-model="nic.production_subnet_id" required><option value="">Select production network</option><option v-for="row in subnets.filter(s => s.extId !== nic.quarantine_subnet_id)" :key="row.extId" :value="row.extId">{{ row.name || row.extId }}</option></select></label>
    </div>
  </fieldset>
</template>
