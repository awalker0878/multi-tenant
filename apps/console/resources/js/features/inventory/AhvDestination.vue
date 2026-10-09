<script setup lang="ts">
import { computed } from 'vue';
import type { AhvDestinationSelection, AhvTargetCapabilityProfile } from './contracts';
const props = defineProps<{ profile: AhvTargetCapabilityProfile; sourceFirmware: string | null; sourceSecurityIds: string[] | null; sourceCategoryPresent: boolean }>();
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
      <label v-if="model.nics.length">Network scope<select v-model="model.vpc_id" @change="changeVpc"><option :value="null">Cluster VLAN networks</option><option v-for="row in profile.vpcs" :key="row.extId" :value="row.extId">{{ row.name || row.extId }}</option></select></label>
    </div>
    <fieldset v-if="sourceCategoryPresent"><legend>API-observed destination categories (source categories exist)</legend><label v-for="row in profile.categories" :key="row.extId" class="mr-4 inline-flex gap-2"><input v-model="model.category_ids" type="checkbox" :value="row.extId" class="w-auto" />{{ row.key }}: {{ row.value }}</label></fieldset>
    <p v-if="sourceSecurityIds === null" role="alert">Source security policies have not been reliably collected. No destination policies can be selected. Refresh or commission source policy discovery.</p>
    <section v-else-if="sourceSecurityIds.length > 0" role="alert">
      <h3 class="font-semibold">Security policies require native rule qualification</h3>
      <p>Prism reports {{ profile.policies.filter(p => p.state === 'ENFORCE').length }} enforced policy records. Their existence does not establish which application flows or isolation requirements they enforce. Destination policy selection is disabled until rule bodies, referenced groups and receiving-path behavior are independently verified. Existing policies will be selectable by native ID only after that qualification.</p>
    </section>
    <div v-for="disk in model.disks" :key="disk.source_key"><label>Source disk {{ disk.source_key }} → SCSI slot<input v-model.number="disk.index" type="number" min="0" :max="model.disks.length - 1" required /></label></div>
    <div v-for="nic in model.nics" :key="nic.source_key" class="grid gap-4 md:grid-cols-2">
      <label>NIC {{ nic.source_key }} quarantine subnet<select v-model="nic.quarantine_subnet_id" required><option value="">Select quarantine network</option><option v-for="row in subnets" :key="row.extId" :value="row.extId">{{ row.name || row.extId }}</option></select></label>
      <label>NIC {{ nic.source_key }} production subnet<select v-model="nic.production_subnet_id" required><option value="">Select production network</option><option v-for="row in subnets.filter(s => s.extId !== nic.quarantine_subnet_id)" :key="row.extId" :value="row.extId">{{ row.name || row.extId }}</option></select></label>
    </div>
  </fieldset>
</template>
