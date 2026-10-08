<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { Link, router } from '@inertiajs/vue3';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';
import type { NativeJob } from '../../features/jobs/native';
const props = defineProps<{ tenantId: string; base: string; initial: NativeJob & { control_allowed?: boolean } }>();
const job = ref<typeof props.initial | null>(props.initial), busy = ref(false), error = ref(''), unavailable = ref(false);
let active = true, polling = false, timer: ReturnType<typeof setTimeout> | undefined, generation = 0;
const controllers = new Set<AbortController>();
const measurements = computed(() => job.value?.measurements);
const stageMeasurements = computed(() => new Map(measurements.value?.operations.map(row => [row.operation_id, row]) ?? []));
const observedTime = (seconds: number | null) => seconds === null ? 'Not observed' : new Date(seconds * 1000).toLocaleString();
const elapsed = (seconds: number | null | undefined) => seconds == null ? 'Not measured' : seconds < 60 ? `${seconds} s` : `${Math.floor(seconds / 60)} min ${seconds % 60} s`;
const bytes = (value: number) => `${value.toLocaleString()} bytes (${(value / 1024 ** 3).toFixed(2)} GiB)`;
const holdAction = computed(() => {
    if (!job.value?.hold_reason) return null;
    if (job.value.transfer_continuation_candidate) return 'An operator may continue the immutable download after checking retained bytes, current approval and the original deadline.';
    if (job.value.hold_reason === 'native_stop_requested') return 'An operator must review the recorded stages and request a separate approved recovery or cutover plan.';
    if (/expired|approval|authority/.test(job.value.hold_reason)) return 'The approving owner must renew the exact plan authority before further work.';
    return 'A platform operator must reconcile the native outcome and its independent evidence. Preserve the source and destination until an approved recovery decision is recorded.';
});
async function json(url: string, body?: object) {
    const controller = new AbortController(); controllers.add(controller);
    const deadline = setTimeout(() => controller.abort(), body ? 55000 : 15000);
    try {
        const headers: Record<string, string> = { Accept: 'application/json' };
        if (body) {
            headers['Content-Type'] = 'application/json';
            const xsrf = document.cookie.split('; ').find(v => v.startsWith('XSRF-TOKEN='));
            if (xsrf) headers['X-XSRF-TOKEN'] = decodeURIComponent(xsrf.slice(11));
        }
        const response = await fetch(url, { method: body ? 'POST' : 'GET', headers, body: body ? JSON.stringify(body) : undefined, credentials: 'same-origin', cache: 'no-store', redirect: 'manual', signal: controller.signal });
        if (response.type === 'opaqueredirect' || [401, 403, 404, 419].includes(response.status)) {
            active = false; job.value = null; unavailable.value = true; router.clearHistory(); window.location.replace('/account'); throw new Error('Access changed');
        }
        if (!response.headers.get('Content-Type')?.includes('application/json')) throw new Error('State unavailable');
        const value = await response.json();
        if (!response.ok) throw new Error(String(value.error ?? 'Request held').replaceAll('_', ' '));
        return value as typeof props.initial;
    } finally { clearTimeout(deadline); controllers.delete(controller); }
}
async function refresh() {
    if (!active || polling || busy.value || document.hidden) return;
    polling = true; clearTimeout(timer); const observedGeneration = generation;
    try {
        const next = await json(`${props.base}/status`);
        if (!active || generation !== observedGeneration) return;
        if (next.job_id !== props.initial.job_id || next.tenant_id !== props.tenantId
            || next.scope.site_id !== props.initial.scope.site_id || next.scope.environment !== props.initial.scope.environment
            || next.scope.resource_id !== props.initial.scope.resource_id || next.revision < (job.value?.revision ?? props.initial.revision)) throw new Error('State changed');
        job.value = next; unavailable.value = false;
    }
    catch { if (active && generation === observedGeneration) unavailable.value = true; }
    finally { polling = false; if (active) timer = setTimeout(refresh, 5000); }
}
async function command(action: 'stop' | 'continue-transfer') {
    if (busy.value || unavailable.value || !job.value?.control_allowed) return;
    busy.value = true; error.value = ''; generation++; clearTimeout(timer);
    for (const controller of controllers) controller.abort();
    try { await json(`${props.base}/commands`, { action, expected_revision: job.value.revision }); }
    catch (e) { if (active) { unavailable.value = true; error.value = `${e instanceof Error ? e.message : 'Outcome uncertain'}. Refresh current state before another command.`; } }
    finally { busy.value = false; if (active) await refresh(); }
}
function visible() { if (!document.hidden) void refresh(); }
function hide() { job.value = null; unavailable.value = true; for (const controller of controllers) controller.abort(); }
onMounted(() => { timer = setTimeout(refresh, 5000); document.addEventListener('visibilitychange', visible); window.addEventListener('pageshow', visible); window.addEventListener('pagehide', hide); });
onUnmounted(() => { active = false; clearTimeout(timer); hide(); document.removeEventListener('visibilitychange', visible); window.removeEventListener('pageshow', visible); window.removeEventListener('pagehide', hide); });
</script>
<template>
<CatalogueLayout title="Native migration stages" :tenant-id="tenantId">
    <p v-if="unavailable" role="alert">Current state is unavailable. Controls are paused.</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <button :disabled="busy" @click="refresh">Refresh current state</button>
    <section v-if="job" class="mt-6 space-y-4">
        <h2 class="text-xl font-semibold">Migration state: {{ job.state }}</h2>
        <section v-if="job.hold_reason" class="rounded border border-amber-600 p-4"><h3 class="font-semibold">Hold: {{ job.hold_reason.replaceAll('_', ' ') }}</h3><p class="mt-2">{{ holdAction }}</p></section>
        <p>Revision {{ job.revision }}. Each completed stage requires independent observations.</p>
        <section v-if="measurements" class="rounded border border-slate-300 p-4" aria-label="Measured migration progress">
            <h3 class="font-semibold">{{ measurements.completed_stages }} of {{ measurements.total_stages }} stages independently verified</h3>
            <progress class="my-3 w-full" :max="measurements.total_stages || 1" :value="measurements.completed_stages" aria-label="Independently verified stages"></progress>
            <p>Measured at {{ observedTime(measurements.observed_at) }}. Job admitted {{ observedTime(measurements.started_at) }}.</p>
            <p class="mt-2 text-sm">Stage counts do not predict completion time. Elapsed time includes time awaiting independent verification.</p>
            <div v-if="measurements.transfer" class="mt-4 border-t pt-3">
                <p><strong>Retained transfer bytes:</strong> {{ bytes(measurements.transfer.bytes_completed) }} across {{ measurements.transfer.disks_completed }} completed disks.</p>
                <p>Worker custody journal observed {{ observedTime(measurements.transfer.measured_at) }}. Artifact {{ measurements.transfer.artifact_complete ? 'complete; independent stage verification remains required' : 'incomplete' }}.</p>
                <p class="text-sm">Only durably retained disk bytes count. Partial disk downloads and a completion estimate are unavailable.</p>
            </div>
            <p v-else class="mt-3">Retained transfer measurements are unavailable.</p>
        </section>
        <div class="overflow-x-auto"><table class="w-full text-left"><caption class="text-left font-semibold">Recorded stages</caption><thead><tr><th>Stage</th><th>Effect</th><th>Independent evidence</th><th>Measured elapsed</th><th>Last observation</th></tr></thead><tbody><tr v-for="operation in job.operations" :key="operation.operation_id" class="border-t"><td class="p-3">{{ operation.stage.replaceAll('_', ' ') }}</td><td class="p-3">{{ operation.redeemed ? 'Dispatched' : 'Prepared' }}</td><td class="p-3">{{ operation.observation_digest ? 'Verified' : 'Awaiting verification' }}</td><td class="p-3">{{ elapsed(stageMeasurements.get(operation.operation_id)?.elapsed_seconds) }}</td><td class="p-3">{{ observedTime(stageMeasurements.get(operation.operation_id)?.observed_at ?? null) }}</td></tr></tbody></table></div>
        <div v-if="job.control_allowed" class="flex flex-wrap gap-3">
            <button v-if="!job.stopped && ['prepared', 'running', 'held'].includes(job.state)" :disabled="busy || unavailable" @click="command('stop')">Stop migration</button>
            <button v-if="job.transfer_continuation_candidate" :disabled="busy || unavailable" @click="command('continue-transfer')">Continue immutable download</button>
        </div>
        <p v-if="job.transfer_continuation_candidate">Continuation verifies retained bytes and current approval, excludes concurrent writers, and keeps the original deadline. It requires a commissioned resumable archive.</p>
        <p>Stopping holds future effects. Recovery and production cutover require their approved plans. Native qualification: {{ job.native_qualification.replaceAll('_', ' ') }}.</p>
        <Link :href="`/tenants/${tenantId}/applications/${job.scope.resource_id}/environments/${job.scope.environment}/planning/migration-support/${job.scope.site_id}`" class="underline">Review directional qualification and remaining blockers</Link>
    </section>
</CatalogueLayout>
</template>
