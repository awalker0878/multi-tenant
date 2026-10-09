<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { Link, router, useForm } from '@inertiajs/vue3';
import { capabilityDefinitions } from '../../features/planning/capabilityDefinitions';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';

type Platform = { platform: string; installation_id: string; versions: Record<string, string> };
type ApiAlert = { capability_id: string; side: 'source' | 'target'; severity: 'blocker' | 'warning'; reason: string; impact: string; action: string; omission_accepted: boolean };
type ApiCase = { capability_id: string; side: 'source' | 'target'; criticality: 'critical' | 'optional'; status: string; reason: string; selected_api_family: string | null; selected_api_version: string | null; evidence_sha256: string | null; omission_accepted: boolean };
type ApiAssessment = { status: 'eligible' | 'conditional' | 'blocked' | 'unknown'; operationally_eligible: boolean; cases: ApiCase[]; administrator_alerts: ApiAlert[] };
type Route = { route_id: string; guest: string; guest_profile_sha256: string; method: string; source: Platform; target: Platform; constraints: Record<string, string | number>; exclusions: string[]; blockers: string[]; native_qualified: boolean; operationally_accepted: boolean; api_compatibility?: ApiAssessment };
type Support = { tranche_sha256: string; release_sha256: string; directions: { direction: string; state: string; routes: Route[] }[] };
const props = defineProps<{ tenantId: string; siteId: string; applicationId: string; environment: string; support: Support }>();
const current = ref(props.support);
const unavailable = ref(false);
const url = `/tenants/${props.tenantId}/applications/${props.applicationId}/environments/${props.environment}/planning/migration-support/${props.siteId}`;
let active = true, running = false;
let controller: AbortController | undefined;
let timer: ReturnType<typeof setTimeout> | undefined;
async function refresh() {
  if (!active || running) return;
  if (document.hidden) { timer = setTimeout(refresh, 15_000); return; }
  clearTimeout(timer); running = true;
  const request = new AbortController(); controller = request;
  const deadline = setTimeout(() => request.abort(), 12_000);
  try {
    const response = await fetch(url + '/status', { credentials: 'same-origin', cache: 'no-store', redirect: 'manual', headers: { Accept: 'application/json' }, signal: request.signal });
    if (!active || request.signal.aborted) return;
    if (response.type === 'opaqueredirect' || [401, 403, 404].includes(response.status)) { active = false; router.clearHistory(); window.location.replace('/account'); return; }
    if (!response.ok || !response.headers.get('Content-Type')?.includes('application/json')) throw new Error();
    const data = await response.json() as { available: boolean; support: Support };
    if (!active || request.signal.aborted) return;
    if (!data.available || data.support.directions.length !== capabilityDefinitions.platforms.length ** 2) throw new Error();
    current.value = data.support; unavailable.value = false;
    void refreshFlowChoices();
  } catch { if (active) unavailable.value = true; }
  finally { clearTimeout(deadline); running = false; if (active) timer = setTimeout(refresh, 15_000); }
}
function visible() { if (!document.hidden) void refresh(); }
function hide() { unavailable.value = true; controller?.abort(); }
onMounted(() => { timer = setTimeout(refresh, 15_000); document.addEventListener('visibilitychange', visible); window.addEventListener('pagehide', hide); window.addEventListener('pageshow', visible); });
onUnmounted(() => { active = false; controller?.abort(); clearTimeout(timer); document.removeEventListener('visibilitychange', visible); window.removeEventListener('pagehide', hide); window.removeEventListener('pageshow', visible); });
const versions = (platform: Platform) => Object.entries(platform.versions).map(([key, value]) => `${key}: ${value}`).join('; ');

type NativeChoice = {
  source_flow_id: string; source: { from: string; to: string; protocol: string; port: number | null };
  required: boolean; destination_firewall_rule_ids: string[]; destination_route_ids: string[];
  status: 'choices_observed' | 'held_unobserved'; native_write_authorized: false;
};
type NativeBinding = { source_flow_id: string; rule_native_ref: string; route_native_ref: string };
type NativeOmission = { source_flow_id: string; reason_code: string };
type FlowChoices = {
  context_sha256: string; revision: number; expires_at: number; choices: NativeChoice[];
  selections: NativeBinding[]; omissions: NativeOmission[]; holds: string[]; status: 'eligible' | 'held' | 'invalidated';
  native_write_authorized: false;
};
const flowBase = url + '/flow-choices';
const flowSave = url + '/flow-selections';
const flowState = ref<FlowChoices | null>(null);
const flowFailure = ref('');
const flowBusy = ref(false);
const flowForm = useForm({
  command_key: crypto.randomUUID(), revision: 0, context_sha256: '',
  selections: [] as NativeBinding[], omissions: [] as NativeOmission[],
});
let submittedFlowFingerprint = '';
const missingChoices = computed(() => flowState.value?.choices.filter(c =>
  c.required && (!c.destination_firewall_rule_ids.length || !c.destination_route_ids.length)) ?? []);
const selectionsComplete = computed(() => Boolean(flowState.value) && flowState.value!.choices.every(c => {
  const selected = flowForm.selections.find(s => s.source_flow_id === c.source_flow_id);
  return !c.required || (selected
    && c.destination_firewall_rule_ids.includes(selected.rule_native_ref)
    && c.destination_route_ids.includes(selected.route_native_ref));
}));
function flowBinding(id: string): NativeBinding {
  const current = flowForm.selections.find(s => s.source_flow_id === id);
  if (current) return current;
  const created = { source_flow_id: id, rule_native_ref: '', route_native_ref: '' };
  flowForm.selections.push(created);
  return created;
}
function flowSelection(id: string, side: 'rule_native_ref' | 'route_native_ref'): string {
  return flowForm.selections.find(s => s.source_flow_id === id)?.[side] ?? '';
}
function selectFlow(id: string, side: 'rule_native_ref' | 'route_native_ref', value: string) {
  flowBinding(id)[side] = value;
  if (value) flowForm.omissions = flowForm.omissions.filter(o => o.source_flow_id !== id);
}
function omissionFor(id: string): string {
  return flowForm.omissions.find(o => o.source_flow_id === id)?.reason_code ?? '';
}
function requestOmission(id: string, reason: string) {
  flowForm.omissions = flowForm.omissions.filter(o => o.source_flow_id !== id);
  if (reason) {
    flowForm.omissions.push({ source_flow_id: id, reason_code: reason });
    flowForm.selections = flowForm.selections.filter(s => s.source_flow_id !== id);
  }
}
async function refreshFlowChoices(): Promise<void> {
  if (!active || flowBusy.value) return;
  flowBusy.value = true;
  try {
    const response = await fetch(flowBase, { credentials: 'same-origin', cache: 'no-store',
      redirect: 'manual', headers: { Accept: 'application/json' } });
    if (!active) return;
    if ([401, 403, 404].includes(response.status) || response.type === 'opaqueredirect') {
      flowState.value = null; flowFailure.value = 'Application flow access is no longer authorized.';
      return;
    }
    if (!response.ok || !response.headers.get('Content-Type')?.includes('application/json')) throw new Error();
    const payload = await response.json() as { available: boolean; flow_choices: FlowChoices };
    const updated = payload.flow_choices;
    if (!payload.available || !updated || updated.native_write_authorized !== false) throw new Error();
    if (flowForm.context_sha256 !== updated.context_sha256 || flowForm.revision !== updated.revision) {
      flowForm.context_sha256 = updated.context_sha256;
      flowForm.revision = updated.revision;
      flowForm.selections = updated.selections.map(s => ({ ...s }));
      flowForm.omissions = updated.omissions.map(o => ({ ...o }));
      flowForm.command_key = crypto.randomUUID();
      submittedFlowFingerprint = '';
      flowForm.clearErrors();
    }
    flowState.value = updated;
    flowFailure.value = '';
  } catch {
    if (active) { flowState.value = null; flowFailure.value = 'Source application intent or independent destination evidence could not be refreshed. Choices are blocked.'; }
  } finally { flowBusy.value = false; }
}
function saveFlowChoices() {
  if (!selectionsComplete.value || flowForm.processing || flowBusy.value || unavailable.value || flowFailure.value || !flowState.value) return;
  // An optional application dependency may be left unmapped; an incomplete
  // optional selection is not an operator-created rule and is never posted.
  flowForm.selections = flowForm.selections.filter(s =>
    Boolean(s.rule_native_ref) && Boolean(s.route_native_ref));
  const fingerprint = JSON.stringify({
    revision: flowForm.revision,
    context_sha256: flowForm.context_sha256,
    selections: flowForm.selections, omissions: flowForm.omissions,
  });
  if (fingerprint !== submittedFlowFingerprint) {
    flowForm.command_key = crypto.randomUUID();
    submittedFlowFingerprint = fingerprint;
  }
  flowForm.post(flowSave, {
    preserveScroll: true,
    onSuccess: () => { void refreshFlowChoices(); },
    onError: () => { void refreshFlowChoices(); },
  });
}
onMounted(() => { void refreshFlowChoices(); });

</script>

<template>
  <CatalogueLayout title="Directional migration support" :tenant-id="tenantId">
    <Link :href="`/tenants/${tenantId}/inventory/sites/${siteId}/migration-fleet`" class="text-teal-800 underline">Migration fleet</Link>
    <section class="mt-5 rounded border border-slate-300 p-4" aria-label="Source-approved application flow mapping">
      <h2 class="text-lg font-semibold">Required application flows → existing destination controls</h2>
      <p class="mt-2">These dependencies come from the verified application owner's Planning intent—not from VM NICs or generic firewall ACLs. Select only API-discovered destination firewall rules and routes. Save records the choices, but does not authorize migration or replace independent allow/deny, return-path, and tenant-isolation tests.</p>
      <p v-if="flowFailure" role="alert" class="mt-2 text-red-800">{{ flowFailure }}</p>
      <p v-if="!flowState" class="mt-2">An approved application migration assessment and fresh native network observations are required before mapping.</p>
      <template v-else>
        <p class="mt-2" :role="flowState.status === 'eligible' ? 'status' : 'alert'">
          {{ flowState.status === 'eligible' ? 'Current flow selections passed the independent evidence gate.' :
             flowState.status === 'invalidated' ? 'Previously saved flow selections are invalidated by changed source intent or destination observations.' :
             'Application flow selections or independent network/isolation evidence remain held.' }}
        </p>
        <p v-if="flowState.holds.length" role="alert">Holds: {{ flowState.holds.join(', ').replaceAll('_', ' ') }}</p>
        <p v-if="missingChoices.length" role="alert">No matching existing destination rule or route was observed for {{ missingChoices.length }} required application flows. There is no manual resource creation option.</p>
        <div v-for="choice in flowState.choices" :key="choice.source_flow_id" class="mt-3 border-t pt-3">
          <p><strong>{{ choice.source.from }} → {{ choice.source.to }}</strong> · {{ choice.source.protocol }}{{ choice.source.port === null ? '' : ':' + choice.source.port }} · {{ choice.required ? 'Critical / required' : 'Optional' }}</p>
          <div v-if="choice.status === 'choices_observed'" class="mt-1 grid gap-3 md:grid-cols-2">
            <label>Existing destination firewall rule
              <select :value="flowSelection(choice.source_flow_id, 'rule_native_ref')" :disabled="flowForm.processing" @change="selectFlow(choice.source_flow_id, 'rule_native_ref', ($event.target as HTMLSelectElement).value)">
                <option value="">Select observed native rule ID</option>
                <option v-for="id in choice.destination_firewall_rule_ids" :key="id" :value="id">{{ id }}</option>
              </select>
            </label>
            <label>Existing destination network route
              <select :value="flowSelection(choice.source_flow_id, 'route_native_ref')" :disabled="flowForm.processing" @change="selectFlow(choice.source_flow_id, 'route_native_ref', ($event.target as HTMLSelectElement).value)">
                <option value="">Select observed native route ID</option>
                <option v-for="id in choice.destination_route_ids" :key="id" :value="id">{{ id }}</option>
              </select>
            </label>
          </div>
          <p v-else role="alert">No qualified native controls match this source-defined flow; migration must remain held.</p>
          <label v-if="!choice.required" class="mt-2 block">Optional dependency disposition (separate approval required)
            <select :value="omissionFor(choice.source_flow_id)" :disabled="flowForm.processing" @change="requestOmission(choice.source_flow_id, ($event.target as HTMLSelectElement).value)">
              <option value="">Migrate using existing native controls</option>
              <option value="retired_dependency">Dependency retired in destination</option>
              <option value="not_required_at_destination">Not required at destination</option>
              <option value="replaced_by_native_service">Replaced by approved native service</option>
              <option value="accepted_service_limitation">Proposed service limitation</option>
            </select>
          </label>
          <p v-if="omissionFor(choice.source_flow_id)" role="alert">This is a request only. A separate receiving approver and independent E4 Assurance proof are required before migration.</p>
        </div>
        <p v-if="flowForm.errors.flow_mapping" role="alert" class="mt-2">{{ flowForm.errors.flow_mapping }}</p>
        <button type="button" class="mt-4 rounded border px-4 py-2" :disabled="!selectionsComplete || flowForm.processing || flowBusy || unavailable || !!flowFailure || flowState.expires_at <= Math.floor(Date.now() / 1000)" @click="saveFlowChoices">Save reviewed application flow selections</button>
        <button type="button" class="ml-3 mt-4 underline" :disabled="flowBusy" @click="refreshFlowChoices">Refresh native options</button>
      </template>
    </section>
    <p class="mt-4">Each direction is assessed independently. The versions, guest profile, method and constraints below must all match. A selected route is a delivery commitment; qualification and receiving acceptance are separate gates.</p>
    <p v-if="unavailable" role="alert" class="mt-4 text-red-800">Current support could not be verified. Displayed results are stale; restore the Planning and Assurance connections before proceeding.</p>
    <table class="mt-4 w-full text-left text-sm">
      <thead><tr><th class="p-2">Direction</th><th class="p-2">Exact route and constraints</th><th class="p-2">Evidence and next action</th></tr></thead>
      <tbody><tr v-for="direction in current.directions" :key="direction.direction" class="border-t align-top">
        <th class="p-2">{{ direction.direction.replace('->', ' → ') }}</th>
        <td v-if="!direction.routes.length" class="p-2">No selected implementation tuple.</td>
        <td v-else class="p-2"><div v-for="route in direction.routes" :key="route.route_id" class="mb-4">
          <p><strong>{{ route.guest }} · {{ route.method.replaceAll('_', ' ') }}</strong></p>
          <p>Source: {{ versions(route.source) }}</p><p>Destination: {{ versions(route.target) }}</p>
          <p>Installations: {{ route.source.installation_id }} → {{ route.target.installation_id }}</p>
          <details><summary class="cursor-pointer underline">Requirements and limitations</summary>
            <p class="break-all">Guest profile: {{ route.guest_profile_sha256 }}</p>
            <dl><template v-for="(value, key) in route.constraints" :key="key"><dt>{{ key.replaceAll('_', ' ') }}</dt><dd class="mb-2 break-all">{{ value }}</dd></template></dl>
            <p v-for="exclusion in route.exclusions" :key="exclusion">{{ exclusion }}</p>
          </details>
        </div></td>
        <td class="p-2"><p v-if="!direction.routes.length">Delivery gap. Platform engineering must implement and independently qualify this direction; it remains part of any-to-any scope.</p>
          <div v-for="route in direction.routes" :key="route.route_id" class="mb-4">
            <p>Native qualification: {{ !unavailable && route.native_qualified ? 'Accepted' : 'Held' }}</p>
            <p>Operating acceptance: {{ !unavailable && route.operationally_accepted ? 'Accepted' : 'Pending' }}</p>
            <p v-if="!route.api_compatibility" role="status" class="text-amber-900">
              Per-feature API version discovery is not yet enrolled for this historical route.
              Existing route-level qualification is not a feature-by-feature compatibility claim.
            </p>
            <section v-if="route.api_compatibility" class="mt-2 border-l-4 border-amber-600 pl-3" aria-label="API feature migration compatibility">
              <p class="font-semibold">Migration API compatibility: {{ unavailable ? 'Unknown — refresh required' : route.api_compatibility.status }}</p>
              <p v-if="route.api_compatibility.administrator_alerts.length && !unavailable" role="alert" class="font-semibold">
                {{ route.api_compatibility.administrator_alerts.length }} feature{{ route.api_compatibility.administrator_alerts.length === 1 ? '' : 's' }} cannot be transferred unchanged.
              </p>
              <ul v-if="!unavailable" class="list-disc pl-5">
                <li v-for="alert in route.api_compatibility.administrator_alerts" :key="alert.side + ':' + alert.capability_id" class="mb-2">
                  <strong>{{ alert.severity === 'blocker' ? 'Critical — blocks migration' : 'Optional — administrator action required' }}</strong>:
                  {{ alert.capability_id }} ({{ alert.side }}); {{ alert.reason.replaceAll('_', ' ') }}.
                  <span>{{ alert.impact }}</span>
                  <span v-if="alert.omission_accepted">Omission independently accepted, subject to plan revalidation.</span>
                  <span v-else>{{ alert.action.replaceAll('_', ' ') }}.</span>
                </li>
              </ul>
              <details v-if="!unavailable" class="mt-2">
                <summary class="cursor-pointer underline">Required API operations and selected versions</summary>
                <table class="w-full text-xs">
                  <thead><tr><th scope="col">Feature</th><th scope="col">Side</th><th scope="col">Importance</th><th scope="col">Evidence status</th><th scope="col">Selected API</th></tr></thead>
                  <tbody>
                    <tr v-for="operation in route.api_compatibility.cases" :key="operation.side + ':' + operation.capability_id">
                      <td>{{ operation.capability_id }}</td>
                      <td>{{ operation.side }}</td>
                      <td>{{ operation.criticality }}</td>
                      <td>{{ operation.status }}</td>
                      <td>{{ operation.selected_api_family && operation.selected_api_version ? operation.selected_api_family + ' ' + operation.selected_api_version : 'Unknown — no qualified release' }}</td>
                    </tr>
                  </tbody>
                </table>
              </details>
              <p v-if="route.api_compatibility.status !== 'eligible' || unavailable" class="text-red-800">
                No migration approval or native write is permitted until every critical requirement is qualified and optional omissions are explicitly accepted.
              </p>
            </section>
            <p v-for="blocker in route.blockers" :key="blocker">{{ blocker.replaceAll('_', ' ') }}</p>
            <p v-if="route.blockers.length">Qualification owner: supply current independent evidence for this exact release and route in Assurance. Rejected, expired or revoked evidence must be resolved before admission.</p>
          </div>
        </td>
      </tr></tbody>
    </table>
    <p class="mt-4 break-all text-xs">Release: {{ current.release_sha256 }} · Tranche: {{ current.tranche_sha256 }}</p>
  </CatalogueLayout>
</template>
