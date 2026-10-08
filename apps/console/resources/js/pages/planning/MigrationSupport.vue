<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { Link, router } from '@inertiajs/vue3';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';

type Platform = { platform: string; installation_id: string; versions: Record<string, string> };
type Route = { route_id: string; guest: string; guest_profile_sha256: string; method: string; source: Platform; target: Platform; constraints: Record<string, string | number>; exclusions: string[]; blockers: string[]; native_qualified: boolean; operationally_accepted: boolean };
type Support = { tranche_sha256: string; release_sha256: string; directions: { direction: string; state: string; routes: Route[] }[] };
const props = defineProps<{ tenantId: string; siteId: string; applicationId: string; environment: string; support: Support }>();
const current = ref(props.support);
const unavailable = ref(false);
const url = `/tenants/${props.tenantId}/applications/${props.applicationId}/environments/${props.environment}/planning/migration-support/${props.siteId}`;
const controller = new AbortController();
let timer: ReturnType<typeof setTimeout> | undefined;
async function refresh() {
  try {
    const response = await fetch(url + '/status', { credentials: 'same-origin', cache: 'no-store', redirect: 'manual', headers: { Accept: 'application/json' }, signal: controller.signal });
    if (response.type === 'opaqueredirect' || [401, 403, 404].includes(response.status)) { controller.abort(); router.clearHistory(); window.location.replace('/account'); return; }
    if (!response.ok) throw new Error();
    const data = await response.json() as { available: boolean; support: Support };
    if (!data.available || data.support.directions.length !== 9) throw new Error();
    current.value = data.support; unavailable.value = false;
  } catch { if (!controller.signal.aborted) unavailable.value = true; }
  finally { if (!controller.signal.aborted) timer = setTimeout(refresh, 15_000); }
}
onMounted(() => { timer = setTimeout(refresh, 15_000); });
onUnmounted(() => { controller.abort(); clearTimeout(timer); });
const versions = (platform: Platform) => Object.entries(platform.versions).map(([key, value]) => `${key}: ${value}`).join('; ');
</script>

<template>
  <CatalogueLayout title="Directional migration support" :tenant-id="tenantId">
    <Link :href="`/tenants/${tenantId}/inventory/sites/${siteId}/migration-fleet`" class="text-teal-800 underline">Migration fleet</Link>
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
            <p v-for="blocker in route.blockers" :key="blocker">{{ blocker.replaceAll('_', ' ') }}</p>
            <p v-if="route.blockers.length">Qualification owner: supply current independent evidence for this exact release and route in Assurance. Rejected, expired or revoked evidence must be resolved before admission.</p>
          </div>
        </td>
      </tr></tbody>
    </table>
    <p class="mt-4 break-all text-xs">Release: {{ current.release_sha256 }} · Tranche: {{ current.tranche_sha256 }}</p>
  </CatalogueLayout>
</template>
