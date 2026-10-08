<script setup lang="ts">
import { computed } from 'vue';
import type { AhvDestinationSelection, AhvTargetCapabilityProfile } from './contracts';
const props = defineProps<{ profile: AhvTargetCapabilityProfile; sourceFirmware: string | null; sourceSecurityIds: string[] | null; sourceCategoryPresent: boolean }>();
const model = defineModel<AhvDestinationSelection>({ required: true });
const subnets = computed(() => props.profile.subnets.filter(s => s.vpcReference === model.value.vpc_id));
function securityMappingChanged() {
  model.value.policy_ids = model.value.security_mappings.map(item => item.destination_id).filter(Boolean);
}
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
    <fieldset v-else-if="sourceSecurityIds.length > 0">
      <legend>Map existing source security groups to API-observed, enforced destination policies</legend>
      <div v-for="mapping in model.security_mappings" :key="mapping.source_id">
        <label>Source security group {{ mapping.source_id }}
          <select v-model="mapping.destination_id" required @change="securityMappingChanged">
            <option value="">Select existing enforced destination policy</option>
            <option v-for="policy in profile.policies.filter(p => p.state === 'ENFORCE')" :key="policy.extId" :value="policy.extId">{{ policy.name || policy.extId }}</option>
          </select>
        </label>
      </div>
      <p v-if="!profile.policies.some(p => p.state === 'ENFORCE')" role="alert">No enforced destination policies were returned by the destination API. Migration mapping is blocked.</p>
      <p>These are destination API records. Cross-platform policy semantics are unqualified; this selection is a draft and confirmation remains blocked until independent allow/deny and application-flow verification.</p>
    </fieldset>
    <div v-for="disk in model.disks" :key="disk.source_key"><label>Source disk {{ disk.source_key }} → SCSI slot<input v-model.number="disk.index" type="number" min="0" :max="model.disks.length - 1" required /></label></div>
    <div v-for="nic in model.nics" :key="nic.source_key" class="grid gap-4 md:grid-cols-2">
      <label>NIC {{ nic.source_key }} quarantine subnet<select v-model="nic.quarantine_subnet_id" required><option value="">Select quarantine network</option><option v-for="row in subnets" :key="row.extId" :value="row.extId">{{ row.name || row.extId }}</option></select></label>
      <label>NIC {{ nic.source_key }} production subnet<select v-model="nic.production_subnet_id" required><option value="">Select production network</option><option v-for="row in subnets.filter(s => s.extId !== nic.quarantine_subnet_id)" :key="row.extId" :value="row.extId">{{ row.name || row.extId }}</option></select></label>
    </div>
  </fieldset>
</template>
