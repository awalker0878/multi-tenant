<script setup lang="ts">
import { computed, nextTick, watch } from 'vue';
import { Link, router, useForm } from '@inertiajs/vue3';
import VmwareDestination from '../../features/inventory/VmwareDestination.vue';
import AhvDestination from '../../features/inventory/AhvDestination.vue';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';
import type { MigrationReviewInput, MigrationWorkspace } from '../../features/inventory/contracts';
import { observedTime, useInventoryAccess } from '../../features/inventory/useAccess';
import { migrationHold } from '../../features/inventory/migration-holds';
import featurePolicy from '../../../contracts/migration-feature-policy-v1.json';
const props = defineProps<{ tenantId: string; siteId: string; profileId?: string | null; workspace: MigrationWorkspace; notice: string | null }>();
const base = `/tenants/${props.tenantId}/inventory/sites/${props.siteId}/migration${props.profileId ? `/profiles/${props.profileId}` : ''}`;
const { unavailable, now } = useInventoryAccess(base + '/status');
const saved = props.workspace.review;
const initial = saved?.input && (!props.profileId || saved.input.source_profile_id === props.profileId) ? saved.input : {
  source_profile_id: props.profileId ?? '', target_profile_id: '', method: '', datasets: [],
  owner_inputs: Object.fromEntries(props.workspace.owner_fields.map(field => [field, ''])) as MigrationReviewInput['owner_inputs'],
  objectives: { owner_id: '', acceptance_sha256: '', max_outage_seconds: 0, max_data_loss_bytes: 0 }, overrides: [],
};
const form = useForm({ operation: 'save', command_key: crypto.randomUUID(), revision: saved?.revision ?? null,
  digest: saved?.digest ?? null, review: JSON.parse(JSON.stringify(initial)) as Omit<MigrationReviewInput, 'method'> & { method: string } });
const dirty = computed(() => JSON.stringify(form.review) !== JSON.stringify(initial));
const errors = computed(() => form.errors as Record<string, string>);
const uncertain = computed(() => errors.value.inventory_status === '503');
const blocked = computed(() => form.processing || unavailable.value || uncertain.value || errors.value.inventory_status === '412');
const source = computed(() => props.workspace.profiles.find(p => p.id === form.review.source_profile_id) ?? (saved?.source.id === form.review.source_profile_id ? saved.source : null));
const target = computed(() => props.workspace.profiles.find(p => p.id === form.review.target_profile_id) ?? (saved?.target.id === form.review.target_profile_id ? saved.target : null));
const disks = computed(() => source.value?.facts.profile_type === 'SourceWorkloadProfile' ? source.value.facts.disks : []);
const ahv = computed(() => target.value?.facts.profile_type === 'TargetCapabilityProfile' && target.value.facts.platform === 'ahv' ? target.value.facts : null);
const vmware = computed(() => target.value?.facts.profile_type === 'TargetCapabilityProfile' && target.value.facts.platform === 'vmware' ? target.value.facts : null);
const openstack = computed(() => target.value?.facts.profile_type === 'TargetCapabilityProfile' && target.value.facts.platform === 'openstack' ? target.value.facts : null);
/** Null = source network security not collected, not "no rules". */
const sourceSecurityIds = computed<string[] | null>(() => {
  const facts = source.value?.facts;
  if (!facts || facts.profile_type !== 'SourceWorkloadProfile') return null;
  if (!facts.nics.length) return [];
  if (facts.platform !== 'openstack' || facts.schema_version !== 3) return null;
  const ports = facts.native.metadata.ports;
  if (!Array.isArray(ports) || ports.length !== facts.nics.length || !facts.native_scope) return null;
  const set = new Set<string>();
  const portIds = new Set<string>();
  for (const row of ports) {
    if (typeof row !== 'object' || row === null) return null;
    const port = row as Record<string, unknown>;
    if (typeof port.id !== 'string' || !port.id || portIds.has(port.id)
        || (port.project_id ?? port.tenant_id) !== facts.native_scope
        || port.port_security_enabled !== true || !Array.isArray(port.security_groups)
        || port.security_groups.length > 64
        || !port.security_groups.every(v => typeof v === 'string' && v.length > 0)
        || new Set(port.security_groups).size !== port.security_groups.length) return null;
    portIds.add(port.id);
    for (const id of port.security_groups as string[]) set.add(id);
  }
  return set.size <= 64 ? [...set].sort() : null;
});
function matchingOpenstackGroups(sourceId: string) {
  const facts = source.value?.facts;
  if (!facts || facts.profile_type !== 'SourceWorkloadProfile'
      || facts.platform !== 'openstack' || facts.schema_version !== 3) return [];
  const records = facts.native.metadata.security_groups;
  if (!Array.isArray(records)) return [];
  const sourceRule = records.find(item => typeof item === 'object' && item !== null && (item as Record<string, unknown>).id === sourceId) as Record<string, unknown> | undefined;
  if (!sourceRule || sourceRule.project_id !== facts.native_scope
      || typeof sourceRule.semantics_sha256 !== 'string'
      || !/^[a-f0-9]{64}$/.test(sourceRule.semantics_sha256)) return [];
  return openstack.value?.security_groups?.filter(item =>
    item.project_id === openstack.value?.project_id
    && item.stateful !== null
    && item.semantics_sha256 === sourceRule.semantics_sha256) ?? [];
}
const sourceCategoryPresent = computed(() => {
  const facts = source.value?.facts;
  if (!facts || facts.profile_type !== 'SourceWorkloadProfile' || facts.platform !== 'ahv' || facts.schema_version !== 3) return false;
  const vm = facts.native.metadata.vm as Record<string, unknown> | undefined;
  return Array.isArray(vm?.categories) && vm.categories.length > 0;
});
function syncOpenstackPolicies() {
  // Selection remains a source-key -> observed-target-ID reference, not a rule edit.
  if (form.review.destination?.platform !== 'openstack') return;
  for (const mapping of form.review.destination.security_mappings) {
    if (!matchingOpenstackGroups(mapping.source_id).some(g => g.id === mapping.destination_id)) {
      mapping.destination_id = '';
    }
  }
}

watch(() => [form.review.source_profile_id, form.review.target_profile_id], (_, previous) => {
  if (!previous && form.review.destination) return;
  if (vmware.value) {
    form.review.destination = {
      platform: 'vmware', project_id: vmware.value.project_id, vcenter_uuid: vmware.value.vcenter_uuid,
      folder_id: '', resource_pool_id: '', host_id: '', datastore_id: '', guest_id: '', hardware_version: '',
      firmware: source.value?.facts.profile_type === 'SourceWorkloadProfile' && ['efi', 'bios'].includes(source.value.facts.firmware ?? '') ? source.value.facts.firmware as 'efi' | 'bios' : '',
      disks: disks.value.map((d, index) => ({ source_key: d.key, index })),
      nics: (source.value?.facts.profile_type === 'SourceWorkloadProfile' ? source.value.facts.nics : []).map(n => ({ source_key: n.key, quarantine_network_id: '', production_network_id: '' })),
    };
    form.review.method = 'VM_COLD_EXPORT';
    return;
  }
  if (openstack.value) {
    form.review.destination = sourceSecurityIds.value?.length
      ? { platform: 'openstack', project_id: openstack.value.project_id, security_mappings: sourceSecurityIds.value.map(source_id => ({ source_id, destination_id: '' })) }
      : undefined;
    form.review.method = '';
    return;
  }
  if (!ahv.value) { delete form.review.destination; return; }
  form.review.destination = {
    platform: 'ahv', project_id: ahv.value.project_id, prism_central_id: ahv.value.prism_central_id,
    cluster_id: ahv.value.cluster_id, vpc_id: null, storage_container_id: '', category_ids: [], policy_ids: [], security_mappings: (sourceSecurityIds.value ?? []).map(source_id => ({ source_id, destination_id: '' })), firmware: source.value?.facts.profile_type === 'SourceWorkloadProfile' && ['efi', 'bios'].includes(source.value.facts.firmware ?? '') ? source.value.facts.firmware as 'efi' | 'bios' : '',
    disks: disks.value.map((d, index) => ({ source_key: d.key, index })),
    nics: (source.value?.facts.profile_type === 'SourceWorkloadProfile' ? source.value.facts.nics : []).map(n => ({ source_key: n.key, quarantine_subnet_id: '', production_subnet_id: '' })),
  };
  form.review.method = 'VM_COLD_EXPORT';
}, { immediate: true });
const expired = computed(() => [source.value, target.value].some(p => !p?.current || p.expires_at <= now.value));
const featureDirection = computed(() => featurePolicy.directions.find(
  option => option.source === source.value?.facts.platform && option.target === target.value?.facts.platform,
));
const migrationFeatures = computed(() => featurePolicy.features.map(feature => ({
  ...feature,
  proposal: featureDirection.value?.features.find(item => item.feature_id === feature.id),
})));
// Source observation controls feature *visibility*, not a claim of portability.
// Owner obligations are displayed in their own section even without native facts.
const mandatoryNativeFacts = new Set([
  'platform.api', 'vm.identity', 'vm.power', 'vm.compute',
  'guest.firmware', 'storage.disks',
]);
function sourceFeatureDefined(id: string): boolean {
  const facts = source.value?.facts;
  if (!facts || facts.profile_type !== 'SourceWorkloadProfile') return false;
  const disks = facts.disks;
  const metadata = facts.schema_version === 3 ? facts.native.metadata : null;
  const vm = metadata && typeof metadata.vm === 'object' && metadata.vm !== null
    ? metadata.vm as Record<string, unknown> : null;
  const ports = metadata && Array.isArray(metadata.ports) ? metadata.ports as Array<Record<string, unknown>> : [];
  const records = facts.schema_version === 3 ? facts.native.disk_records : [];
  const sourceGroups = metadata && Array.isArray(metadata.security_groups)
    ? metadata.security_groups as Array<Record<string, unknown>> : [];
  switch (id) {
    case 'platform.api': return typeof facts.api_version === 'string' && facts.api_version.length > 0;
    case 'vm.identity': return typeof facts.vm_id === 'string' && facts.vm_id.length > 0;
    case 'vm.power': return typeof facts.power_state === 'string' && facts.power_state.length > 0;
    case 'vm.compute': return facts.cpu !== null && facts.memory_mb !== null;
    case 'vm.placement': return false; // Native VM identity is not evidence of placement equivalence.
    case 'guest.firmware': return facts.firmware === 'bios' || facts.firmware === 'efi';
    case 'guest.drivers': return false; // Guest IDs do not prove the installed drivers will boot.
    case 'guest.devices': return Boolean(
      vm && (Array.isArray(vm.gpus) && vm.gpus.length
      || Array.isArray(vm.pcieDevices) && vm.pcieDevices.length
      || Array.isArray(vm.cdRoms) && vm.cdRoms.length
      || vm.vtpmConfig)
    );
    case 'storage.disks':
    case 'storage.target':
    case 'storage.transfer': return disks.length > 0;
    case 'storage.controller': return facts.controllers.length > 0
      || disks.some(d => d.controller_key !== null);
    case 'storage.sharing': return disks.some(d => d.backing_chain.some(b => b.sharing))
      || records.some(r => r.metadata?.multiattach === true);
    case 'storage.encryption': return disks.some(d => d.backing_chain.some(b => b.encrypted))
      || records.some(r => r.metadata?.encrypted === true);
    case 'network.nics': return facts.nics.length > 0;
    case 'network.routing': return Boolean(
      metadata && Array.isArray(metadata.routes) && metadata.routes.length > 0
    ); // A port's network ID or fixed IP does not prove routing.
    case 'network.flows': return Boolean(
      metadata && Array.isArray(metadata.application_flows) && metadata.application_flows.length > 0
    ); // A NIC or Neutron policy alone does not establish required application flows.
    case 'network.security': return Boolean(sourceSecurityIds.value?.length)
      && sourceSecurityIds.value!.every(id => sourceGroups.some(g =>
        g.id === id && g.project_id === (facts.schema_version === 3 ? facts.native_scope : null)
        && typeof g.semantics_sha256 === 'string' && /^[a-f0-9]{64}$/.test(g.semantics_sha256)));
    case 'network.qos': return ports.some(p => typeof p.qos_policy_id === 'string' && p.qos_policy_id.length > 0);
    case 'security.scope': return facts.schema_version === 3
      ? typeof facts.native_scope === 'string' && facts.native_scope.length > 0
      : typeof facts.vcenter_uuid === 'string' && facts.vcenter_uuid.length > 0;
    case 'metadata.optional': return Boolean(
      (vm && Array.isArray(vm.categories) && vm.categories.length)
      || (metadata && typeof metadata.server === 'object' && metadata.server !== null
          && typeof (metadata.server as Record<string, unknown>).name === 'string')
    );
    default: return false; // Application / cutover / recovery inputs are not invented native API facts.
  }
}
const displayedMigrationFeatures = computed(() => migrationFeatures.value.filter(feature => sourceFeatureDefined(feature.id)));
const missingSourceFacts = computed(() => migrationFeatures.value.filter(
  feature => feature.criticality === 'critical'
    && (mandatoryNativeFacts.has(feature.id)
      || (feature.id.startsWith('network.') && source.value?.facts.profile_type === 'SourceWorkloadProfile'
        && source.value.facts.nics.length > 0))
    && !sourceFeatureDefined(feature.id)
));

const operatorObligations = computed(() => featurePolicy.operator_requirements.filter(item =>
  item.criticality === 'critical'
  && !(item.attribute_id === 'application.final_delta' && form.review.method === 'VM_COLD_EXPORT')
));
function reviewInputSupplied(path: string | null): boolean {
  if (path === null) return false;
  if (path === 'datasets') return form.review.datasets.length > 0 && disks.value.length > 0 && missing.value.length === 0;
  if (path.startsWith('owner_inputs.')) {
    const key = path.slice('owner_inputs.'.length);
    return Boolean((form.review.owner_inputs as Record<string, string>)[key]?.trim());
  }
  if (path === 'objectives.max_outage_seconds') return Number.isInteger(form.review.objectives.max_outage_seconds) && form.review.objectives.max_outage_seconds >= 0;
  if (path === 'objectives.max_data_loss_bytes') return Number.isInteger(form.review.objectives.max_data_loss_bytes) && form.review.objectives.max_data_loss_bytes >= 0;
  return false;
}
const requiredReviewMissing = computed(() => operatorObligations.value.filter(
  item => item.review_field !== null && !reviewInputSupplied(item.review_field)
));
const operatorExternalObligations = computed(() => operatorObligations.value.filter(item => item.readiness_field !== null));

const missing = computed(() => disks.value.filter(d => !form.review.datasets.some(set => set.disk_keys.includes(d.key))));
const submit = () => form.post(base, { preserveState: 'errors', onError: async () => { await nextTick(); document.getElementById('migration-errors')?.focus(); } });
function act(operation: string) { if (blocked.value) return; form.operation = operation; form.command_key = crypto.randomUUID(); form.clearErrors(); submit(); }
function addDataset() { form.review.datasets.push({ id: crypto.randomUUID(), name: '', disk_keys: [], mounts: [''], consistency_group: '', validation_reference: '' }); }
function addOverride() { form.review.overrides.push({ field: 'application_consistency', interpretation: '', reason: '' }); }
</script>
<template>
  <CatalogueLayout title="Migration readiness review" :tenant-id="tenantId">
    <Link :href="`/tenants/${tenantId}/inventory/sites/${siteId}/configuration`" class="text-teal-800 underline">Environment configuration and API collection</Link>
    <Link :href="`/tenants/${tenantId}/inventory/sites/${siteId}/migration-fleet`" class="ml-4 text-teal-800 underline">Source inventory and migration groups</Link>
    <p class="my-4">Review discovered source and destination facts, account for every disk, and select one migration method. Enter application information and references that the platform APIs cannot determine.</p>
    <p v-if="notice" role="status" class="my-4 border border-teal-600 p-4">{{ notice }}</p>
    <div v-if="Object.keys(errors).length" id="migration-errors" role="alert" tabindex="-1" class="my-4 border border-red-600 p-4"><p v-for="(error, key) in errors" :key="key">{{ key === 'inventory_status' ? '' : error }}</p></div>
    <p v-if="unavailable" role="status">Access cannot currently be checked. Editing is paused.</p>
    <div class="my-4 flex gap-3"><button type="button" class="secondary" :disabled="form.processing" @click="router.get(base)">Refresh findings</button><button v-if="uncertain" type="button" :disabled="form.processing || unavailable" @click="submit">Retry unchanged command</button></div>
    <p v-if="!workspace.profiles.length">No current workload profiles have been collected. Pull the enrolled source and target connections with their migration profile streams enabled.</p>
    <form @submit.prevent="act('save')"><fieldset :disabled="blocked" class="space-y-5">
      <legend class="text-xl font-semibold">Source, destination and method</legend>
      <div class="grid gap-4 md:grid-cols-2">
        <label>Source VM profile<select v-model="form.review.source_profile_id" :disabled="!!profileId" required><option value="">Select observed source</option><option v-if="saved && !workspace.profiles.some(p => p.id === saved?.source.id)" :value="saved.source.id">{{ saved.source.native_id }} — refresh required</option><option v-for="p in workspace.profiles.filter(p => p.profile_type === 'SourceWorkloadProfile')" :key="p.id" :value="p.id">{{ p.facts.platform }} · {{ p.native_id }} · {{ observedTime(p.collected_at) }}{{ p.current ? '' : ' · stale' }}</option></select></label>
        <label>Destination profile<select v-model="form.review.target_profile_id" required><option value="">Select observed destination</option><option v-if="saved && !workspace.profiles.some(p => p.id === saved?.target.id)" :value="saved.target.id">{{ saved.target.native_id }} — refresh required</option><option v-for="p in workspace.profiles.filter(p => p.profile_type === 'TargetCapabilityProfile')" :key="p.id" :value="p.id">{{ p.facts.platform }} · {{ p.native_id }} · {{ observedTime(p.collected_at) }}{{ p.current ? '' : ' · stale' }}</option></select></label>
      </div>
      <label>Explicit migration method<select v-model="form.review.method" required><option value="">Select a method</option><option v-for="method in (ahv || vmware ? ['VM_COLD_EXPORT'] : workspace.methods)" :key="method" :value="method">{{ method.replaceAll('_', ' ') }}</option></select></label>
      <p>Methods require their own qualification. A failed method never selects another method automatically. Cold export retains the source outage throughout movement; delta methods require a qualified final synchronization protocol.</p>
      <section class="rounded border border-slate-300 p-4" aria-labelledby="feature-map-title">
        <h2 id="feature-map-title" class="text-lg font-semibold">Cross-platform feature mapping (not qualification)</h2>
        <p class="mt-2 text-sm">The mapping identifies possible translations, never asserts that this installation supports them. Native API facts must come from Inventory; the application and platform owners supply decisions, and Assurance independently validates required behavior.</p>
        <p v-if="!featureDirection" role="status" class="mt-2">Choose both VM source and destination environments to see their 30 feature mappings.</p>
        <template v-else>
          <p v-if="missingSourceFacts.length" role="alert" class="mt-2">Required source attributes have not been observed for {{ missingSourceFacts.map(item => item.label).join(', ') }}. Destination options for these areas are hidden; restore source discovery instead of inventing values.</p>
          <p class="mt-2 font-medium">{{ source?.facts.platform }} → {{ target?.facts.platform }} · {{ displayedMigrationFeatures.filter(item => item.criticality === 'critical').length }} source-defined critical areas · no native eligibility implied</p>
          <details class="mt-3">
            <summary class="cursor-pointer font-medium">Show feature-by-feature mappings and migration holds</summary>
            <table class="mt-3 w-full text-left text-sm">
              <thead><tr><th scope="col" class="p-2">Feature</th><th scope="col" class="p-2">Required</th><th scope="col" class="p-2">Proposed treatment</th></tr></thead>
              <tbody>
                <tr v-for="feature in displayedMigrationFeatures" :key="feature.id" class="border-t">
                  <td class="p-2"><strong>{{ feature.label }}</strong><p class="text-xs">{{ feature.notes }}</p></td>
                  <td class="p-2">{{ feature.criticality }}</td>
                  <td class="p-2">{{ feature.proposal?.mapping_proposal.replaceAll('_', ' ') ?? 'Unassessed' }}<p class="text-xs">Unknown until installed API and independent receiving evidence are reviewed.</p></td>
                </tr>
              </tbody>
            </table>
          </details>
        </template>
      </section>
      <section class="rounded border border-slate-300 p-4" aria-labelledby="operator-evidence-title">
        <h2 id="operator-evidence-title" class="text-lg font-semibold">Mandatory operator and independent evidence</h2>
        <p class="mt-2 text-sm">The Console must collect the owner inputs; it must not ask for or overwrite API-discovered CPU, disks, power, native network configuration or installed versions. Supplying a reference is not verification.</p>
        <p role="status" class="mt-2">{{ requiredReviewMissing.length }} in-review mandatory inputs missing · {{ operatorExternalObligations.length }} requirements also refer to separate operator-readiness records or independent evidence.</p>
        <Link :href="`/tenants/${tenantId}/inventory/sites/${siteId}/operator-inputs`" class="mt-2 inline-block text-teal-800 underline">Open operator readiness and independent verification</Link>
        <details class="mt-3">
          <summary class="cursor-pointer font-medium">Show all applicable owner, security and receiving requirements</summary>
          <table class="mt-3 w-full text-left text-sm">
            <thead><tr><th scope="col" class="p-2">Requirement</th><th scope="col" class="p-2">Console input</th><th scope="col" class="p-2">Verification</th></tr></thead>
            <tbody>
              <tr v-for="item in operatorObligations" :key="item.attribute_id" class="border-t">
                <td class="p-2">{{ item.attribute_id.replaceAll('_', ' ').replaceAll('.', ' · ') }}<p class="text-xs">{{ item.condition }}</p></td>
                <td class="p-2">{{ item.review_field ? (reviewInputSupplied(item.review_field) ? 'Review input supplied' : 'Review input required') : 'Separate operator-readiness input' }}<p v-if="item.readiness_field" class="text-xs">Operator readiness: {{ item.readiness_field.replaceAll('_', ' ') }}</p></td>
                <td class="p-2">{{ item.verification.replaceAll('_', ' ') }}<p class="text-xs">Not approved by this screen</p></td>
              </tr>
            </tbody>
          </table>
        </details>
      </section>
      <AhvDestination v-if="ahv && form.review.destination?.platform === 'ahv'" v-model="form.review.destination" :profile="ahv" :source-firmware="source?.facts.profile_type === 'SourceWorkloadProfile' ? source.facts.firmware : null" :source-security-ids="sourceSecurityIds" :source-category-present="sourceCategoryPresent" />
      <section v-if="openstack && sourceSecurityIds?.length && form.review.destination?.platform === 'openstack'" class="rounded border p-4">
        <h3 class="font-semibold">Existing OpenStack destination security groups</h3>
        <p>Each source group must map to a destination group discovered from Neutron. This selection does not replace independent allow/deny flow validation.</p>
        <div v-for="mapping in form.review.destination.security_mappings" :key="mapping.source_id">
          <label>Source security group {{ mapping.source_id }}
            <select v-model="mapping.destination_id" required @change="syncOpenstackPolicies">
              <option value="">Select a destination API security group</option>
              <option v-for="group in matchingOpenstackGroups(mapping.source_id)" :key="group.id" :value="group.id">{{ group.name }} ({{ group.id }})</option>
            </select>
          </label>
        </div>
        <p v-if="!openstack.security_groups.length" role="alert">No destination security groups were discovered for the target project. No manual destination value is accepted.</p>
        <p v-if="form.review.destination.security_mappings.some(m => matchingOpenstackGroups(m.source_id).length === 0)" role="alert">Only project-scoped destination groups with identical observed policy-rule semantics appear. No matching native group means the migration is held; application-required traffic and deny paths still need separate receiving-environment verification.</p>
      </section>
      <p v-if="sourceSecurityIds === null && source?.facts.profile_type === 'SourceWorkloadProfile' && source.facts.nics.length" role="alert">Source security intent is not discoverable from this profile. Destination policy choices are unavailable until source security evidence is collected.</p>
      <VmwareDestination v-if="vmware && form.review.destination?.platform === 'vmware'" v-model="form.review.destination" :profile="vmware" :source-guest-id="source?.facts.profile_type === 'SourceWorkloadProfile' ? source.facts.guest_id : null" :source-firmware="source?.facts.profile_type === 'SourceWorkloadProfile' ? source.facts.firmware : null" />
      <h2 class="text-xl font-semibold">All disks and application datasets</h2>
      <table class="w-full text-left"><thead><tr><th>Disk key</th><th>Capacity (bytes)</th><th>Dataset coverage</th></tr></thead><tbody><tr v-for="disk in disks" :key="disk.key" class="border-t"><td class="p-2">{{ disk.key }}</td><td>{{ disk.capacity_bytes ?? 'Unknown' }}</td><td>{{ missing.some(d => d.key === disk.key) ? 'Mapping required' : 'Accounted for' }}</td></tr></tbody></table>
      <p v-if="missing.length" role="status">{{ missing.length }} disks still require dataset mapping.</p>
      <fieldset v-for="(dataset, index) in form.review.datasets" :key="dataset.id" class="rounded border border-slate-300 p-4"><legend>Dataset {{ index + 1 }}</legend>
        <div class="grid gap-4 md:grid-cols-2"><label>Name<input v-model="dataset.name" required maxlength="240" /></label><label>Consistency group<input v-model="dataset.consistency_group" required maxlength="240" /></label><label>Mounts or dataset paths (one per line)<textarea :value="dataset.mounts.join('\n')" required @input="dataset.mounts = ($event.target as HTMLTextAreaElement).value.split('\n')"></textarea></label><label>Correctness check reference<input v-model="dataset.validation_reference" required maxlength="240" /></label></div>
        <fieldset class="my-3"><legend>Disks containing this dataset</legend><label v-for="disk in disks" :key="disk.key" class="mr-4 inline-flex gap-2"><input v-model="dataset.disk_keys" type="checkbox" :value="disk.key" class="w-auto" />Disk {{ disk.key }}</label></fieldset>
        <button type="button" class="secondary" @click="form.review.datasets.splice(index, 1)">Remove dataset</button>
      </fieldset>
      <button type="button" class="secondary" :disabled="!disks.length || form.review.datasets.length >= 256" @click="addDataset">Add dataset</button>
      <h2 class="text-xl font-semibold">Application and operating inputs</h2><p>Use owner-approved references. API identities, versions, devices, capacities and readiness holds remain unchanged.</p>
      <div class="grid gap-4 md:grid-cols-2"><label v-for="field in workspace.owner_fields" :key="field" class="capitalize">{{ field.replaceAll('_', ' ') }}<input v-model="form.review.owner_inputs[field]" :required="field !== 'delta_protocol' || form.review.method !== 'VM_COLD_EXPORT'" :disabled="field === 'delta_protocol' && form.review.method === 'VM_COLD_EXPORT'" maxlength="240" /></label></div>
      <h2 class="text-xl font-semibold">Owner objectives</h2><div class="grid gap-4 md:grid-cols-2"><label>Application owner ID<input v-model="form.review.objectives.owner_id" required /></label><label>Acceptance record SHA-256<input v-model="form.review.objectives.acceptance_sha256" required pattern="[0-9a-f]{64}" /></label><label>Maximum outage (seconds)<input v-model.number="form.review.objectives.max_outage_seconds" type="number" min="0" max="31536000" required /></label><label>Maximum data loss (bytes)<input v-model.number="form.review.objectives.max_data_loss_bytes" type="number" min="0" max="9007199254740991" required /></label></div>
      <h2 class="text-xl font-semibold">Reasoned application interpretations</h2><div v-for="(override, index) in form.review.overrides" :key="index" class="grid gap-3 rounded border p-4 md:grid-cols-3"><label>Application field<select v-model="override.field"><option v-for="field in workspace.owner_fields" :key="field" :value="field">{{ field.replaceAll('_', ' ') }}</option></select></label><label>Interpretation<input v-model="override.interpretation" required maxlength="240" /></label><label>Reason and evidence<input v-model="override.reason" required maxlength="240" /></label><button type="button" class="secondary" @click="form.review.overrides.splice(index, 1)">Remove interpretation</button></div>
      <button type="button" class="secondary" :disabled="form.review.overrides.length >= 8" @click="addOverride">Add reasoned interpretation</button>
      <div><button type="submit" :disabled="!source || !target || !form.review.datasets.length || missing.length > 0 || requiredReviewMissing.length > 0">Save migration review</button></div>
    </fieldset></form>
    <section class="my-8 rounded border border-slate-300 p-5"><h2 class="text-xl font-semibold">Confirm the saved review</h2><p v-if="saved">Revision {{ saved.revision }} · {{ saved.confirmation_current && !expired ? 'Confirmed' : 'Review required' }}</p><p class="my-3">Confirmation binds the exact observations, complete disk and dataset map, method and owner inputs. It does not start a migration.</p><ul v-if="saved?.holds.length" class="my-3 list-disc pl-5"><li v-for="hold in saved.holds" :key="hold">{{ migrationHold(hold) }}</li></ul><button type="button" :disabled="blocked || dirty || !saved || expired || requiredReviewMissing.length > 0 || saved.holds.length > 0 || saved.confirmation_current" @click="act('confirm')">Confirm migration review</button></section>
    <section class="my-8"><h2 class="text-xl font-semibold">Original API observations</h2><details v-for="p in [source, target].filter(Boolean)" :key="p!.id" class="my-3 rounded border p-4"><summary>{{ p!.native_id }} · {{ p!.current && p!.expires_at > now ? 'Current' : 'Refresh required' }}</summary><p class="my-3 break-all">Profile {{ p!.digest }}</p><ul class="list-disc pl-5"><li v-for="hold in p!.facts.holds" :key="hold">{{ migrationHold(hold) }}</li></ul><pre class="mt-3 max-h-96 overflow-auto text-sm">{{ JSON.stringify(p!.facts, null, 2) }}</pre></details></section>
  </CatalogueLayout>
</template>
