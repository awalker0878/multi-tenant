<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { Link, router } from '@inertiajs/vue3';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';
import type { Campaign, CampaignList, MemberRequest, Settings } from '../../features/jobs/campaigns';

type View = (Campaign | CampaignList) & { control_allowed?: boolean };
const props = defineProps<{ tenantId: string; base: string; campaignId: string | null; initial: View }>();
const view = ref<View | null>(props.initial);
const detail = computed(() => view.value && 'members' in view.value ? view.value : null);
const listing = computed(() => view.value && 'items' in view.value ? view.value : null);
const phases = ['capture', 'transfer', 'conversion', 'import', 'validation', 'cutover'] as const;
const phaseLimits = ref<Record<typeof phases[number], number>>({ capture: 1, transfer: 1, conversion: 1, import: 1, validation: 1, cutover: 1 });
const name = ref(''), zone = ref(Intl.DateTimeFormat().resolvedOptions().timeZone);
const maxActive = ref(1), stagger = ref(300), failureLimit = ref(1);
const stamp = (hours: number) => new Date(Date.now() + hours * 3600000).toISOString().slice(0, 16);
const windows = ref([{ start: stamp(1), end: stamp(7) }]);
const cutovers = ref([{ start: stamp(1), end: stamp(7) }]);
const blackouts = ref<{ start: string; end: string }[]>([]);
const planId = ref(''), members = ref<(MemberRequest & { mode: string; method: string })[]>([]);
const busy = ref(false), uncertain = ref(false), unavailable = ref(false), error = ref('');
let pending: { url: string; body: object; create: boolean } | null = null;
let active = true, pollRunning = false, timer: ReturnType<typeof setTimeout> | undefined;
let polling: AbortController | undefined;
const disabled = computed(() => busy.value || uncertain.value || unavailable.value);
const terminal = computed(() => detail.value && ['cancelled', 'complete'].includes(detail.value.state));
const time = (seconds: number) => {
    try { return new Date(seconds * 1000).toLocaleString(undefined, { timeZone: detail.value?.settings.timezone ?? zone.value }); }
    catch { return new Date(seconds * 1000).toISOString(); }
};
const duration = (seconds: number | null) => seconds === null ? 'Measurement required' : `${Math.ceil(seconds / 60)} min`;
function hold(reason: string) {
    const measurement = /measurement_required_(\w+)_concurrency_(\d+)/.exec(reason);
    if (measurement) return `Measure ${measurement[1]} with ${measurement[2]} concurrent migrations.`;
    const labels: Record<string, string> = {
        campaign_measurement_required: 'Waiting for current route measurements.',
        campaign_capacity_wait: 'Waiting for observed resource capacity.',
        campaign_window_wait: 'Waiting for a window long enough for this migration.',
        campaign_stagger_wait: 'Waiting for the next staggered start.',
        campaign_dependency_wait: 'Waiting for prerequisite migrations to complete.',
        campaign_outage_group_wait: 'Another migration in this outage group is active.',
        campaign_failure_limit: 'New starts stopped because the failure limit was reached.',
        campaign_owner_unavailable: 'Current migration authority is unavailable.',
        campaign_outage_objective_exceeded: 'The measured duration exceeds the approved outage objective.',
    };
    return labels[reason] ?? reason.replaceAll('_', ' ');
}

function revoked() {
    view.value = null; members.value = []; pending = null; active = false;
    unavailable.value = true; router.cancelAll(); router.clearHistory(); window.location.replace('/account');
}
async function json(url: string, body?: object, signal?: AbortSignal) {
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (body) {
        headers['Content-Type'] = 'application/json';
        const xsrf = document.cookie.split('; ').find(v => v.startsWith('XSRF-TOKEN='));
        if (xsrf) headers['X-XSRF-TOKEN'] = decodeURIComponent(xsrf.slice('XSRF-TOKEN='.length));
    }
    const response = await fetch(url, { method: body ? 'POST' : 'GET', headers, credentials: 'same-origin', cache: 'no-store', redirect: 'manual', body: body ? JSON.stringify(body) : undefined, signal });
    if (response.type === 'opaqueredirect' || [401, 403].includes(response.status)) { revoked(); throw new Error('access_changed'); }
    if (!response.headers.get('Content-Type')?.includes('application/json')) throw new Error('response_unavailable');
    const result = await response.json();
    if (!response.ok) throw Object.assign(new Error(result.error ?? result.message ?? 'Request held'), { status: response.status });
    return result;
}
async function poll() {
    if (!active || pollRunning || document.hidden) return;
    if (busy.value) { timer = setTimeout(poll, 1000); return; }
    pollRunning = true; clearTimeout(timer); polling = new AbortController();
    const deadline = setTimeout(() => polling?.abort(), 15000);
    try {
        const next = await json(`${props.base}${props.campaignId ? '/' + props.campaignId : ''}/status`, undefined, polling.signal) as View;
        if (!active) return;
        if (next.tenant_id !== props.tenantId || (props.campaignId && (!('id' in next) || next.id !== props.campaignId)) || (detail.value && 'revision' in next && next.revision < detail.value.revision)) throw new Error('stale_response');
        view.value = next; unavailable.value = false;
    } catch { if (active) unavailable.value = true; }
    finally { pollRunning = false; clearTimeout(deadline); if (active) timer = setTimeout(poll, unavailable.value ? 15000 : 5000); }
}
async function addPlan() {
    if (disabled.value) return;
    error.value = ''; busy.value = true;
    try {
        if (!/^[0-9a-f-]{36}$/.test(planId.value)) throw new Error('Enter a reviewed plan reference.');
        const p = await json(`${props.base}/plans/${planId.value}`) as { plan_id: string; plan_revision: number; plan_digest: string; mode: string; method: string };
        if (members.value.some(m => m.plan_id === p.plan_id)) throw new Error('This plan is already in the campaign.');
        members.value.push({ ...p, id: crypto.randomUUID(), approval_id: '', depends_on: [], outage_group: null, priority: 50, not_before: 0, deadline: 0 });
        planId.value = '';
    } catch (e) { error.value = e instanceof Error ? e.message.replaceAll('_', ' ') : 'Plan unavailable'; }
    finally { busy.value = false; }
}
function utc(rows: { start: string; end: string }[]) {
    return rows.map(row => {
        const start = Date.parse(row.start + 'Z') / 1000, end = Date.parse(row.end + 'Z') / 1000;
        if (!Number.isInteger(start) || !Number.isInteger(end) || start >= end) throw new Error('Each UTC window needs an end after its start.');
        return { start, end };
    });
}
async function create() {
    if (disabled.value) return;
    try {
        const normal = utc(windows.value), cutover = utc(cutovers.value);
        const settings: Settings = { name: name.value, timezone: zone.value, windows: normal, cutover_windows: cutover, blackouts: utc(blackouts.value), stagger_seconds: stagger.value, max_active: maxActive.value, failure_limit: failureLimit.value, phase_limits: phaseLimits.value };
        const ordered = members.value.map(({ mode: _mode, method: _method, ...m }) => ({ ...m, outage_group: m.outage_group || null, not_before: Math.min(...normal.map(w => w.start)), deadline: Math.max(...normal.map(w => w.end), ...cutover.map(w => w.end)) }));
        pending = { url: props.base, body: JSON.parse(JSON.stringify({ settings, members: ordered, command_key: crypto.randomUUID() })), create: true };
        await submit();
    } catch (e) { error.value = e instanceof Error ? e.message : 'Invalid schedule'; }
}
async function command(action: 'schedule' | 'pause' | 'cancel') {
    if (disabled.value || !detail.value || !view.value?.control_allowed) return;
    pending = { url: `${props.base}/${props.campaignId}/commands`, body: { action, expected_revision: detail.value.revision, command_key: crypto.randomUUID() }, create: false };
    await submit();
}
async function submit() {
    if (!pending || busy.value || !active) return;
    const request = pending; busy.value = true; error.value = '';
    const controller = new AbortController(), deadline = setTimeout(() => controller.abort(), 55000);
    try {
        const receipt = await json(request.url, request.body, controller.signal) as { id: string };
        if (!active) return;
        pending = null; uncertain.value = false;
        if (request.create) { router.visit(`${props.base}/${receipt.id}`); }
    } catch (e) {
        if (!active) return;
        const status = (e as { status?: number }).status;
        uncertain.value = !status || status >= 500;
        error.value = uncertain.value ? 'The response is uncertain. Recover the same command receipt before making changes.' : (e instanceof Error ? e.message.replaceAll('_', ' ') : 'Request held');
        if (!uncertain.value) pending = null;
    } finally { clearTimeout(deadline); busy.value = false; if (active) void poll(); }
}
function visible() { if (!document.hidden) void poll(); }
function hide() { view.value = null; unavailable.value = true; polling?.abort(); }
onMounted(() => { timer = setTimeout(poll, 5000); document.addEventListener('visibilitychange', visible); window.addEventListener('online', visible); window.addEventListener('pagehide', hide); window.addEventListener('pageshow', visible); });
onUnmounted(() => { active = false; clearTimeout(timer); polling?.abort(); document.removeEventListener('visibilitychange', visible); window.removeEventListener('online', visible); window.removeEventListener('pagehide', hide); window.removeEventListener('pageshow', visible); });
</script>

<template>
<CatalogueLayout title="Migration campaigns" :tenant-id="tenantId">
  <p class="max-w-3xl text-slate-700">Schedule reviewed migrations in staggered waves. Every start requires current approval, measured capacity and independent native checks.</p>
  <p v-if="unavailable" role="alert" class="my-4 rounded border border-amber-600 p-3">Current access or campaign state is unavailable. Commands are paused. <button @click="poll">Refresh</button></p>
  <p v-if="error" role="alert" class="my-4 rounded border border-amber-600 p-3">{{ error }}</p>
  <button v-if="uncertain" :disabled="busy || unavailable" @click="submit">Recover unchanged command receipt</button>

  <section v-if="detail" class="mt-6 space-y-5">
    <Link :href="base" class="underline">All campaigns</Link>
    <h2 class="text-xl font-semibold">{{ detail.settings.name }} · {{ detail.state }}</h2>
    <p>Up to {{ detail.settings.max_active }} active migrations, {{ detail.settings.stagger_seconds }} seconds between starts. Stop new starts after {{ detail.settings.failure_limit }} held migrations.</p>
    <p>Schedule time zone: {{ detail.settings.timezone }}.</p>
    <div class="grid gap-4 md:grid-cols-3">
      <section v-for="(rows, label) in { 'Migration windows': detail.settings.windows, 'Cutover windows': detail.settings.cutover_windows, 'Blackouts': detail.settings.blackouts }" :key="label" class="rounded border p-4"><h3 class="font-semibold">{{ label }}</h3><p v-for="w in rows" :key="w.start">{{ time(w.start) }} – {{ time(w.end) }}</p><p v-if="!rows.length">None</p></section>
    </div>
    <div v-if="view?.control_allowed && !terminal" class="flex flex-wrap gap-3">
      <button v-if="detail.state !== 'scheduled'" :disabled="disabled" @click="command('schedule')">{{ detail.state === 'paused' ? 'Resume schedule' : 'Start schedule' }}</button>
      <button v-if="detail.state === 'scheduled'" :disabled="disabled" @click="command('pause')">Pause campaign</button>
      <button :disabled="disabled" @click="command('cancel')">Cancel queued migrations</button>
    </div>
    <p class="text-sm text-slate-600">Pause is checked at effect boundaries. Cancellation removes queued starts and holds active work; it preserves reservations and does not roll back a native migration. Recovery requires a separately approved plan.</p>
    <div class="overflow-x-auto"><table class="w-full text-left"><caption class="mb-3 text-left font-semibold">Migration progress and measured estimates</caption><thead><tr><th>Plan</th><th>State</th><th>Total duration</th><th>Source outage</th><th>Hold</th></tr></thead><tbody><tr v-for="m in detail.members" :key="m.id" class="border-t align-top"><td class="p-3"><span class="break-all">{{ m.specification.plan_id }}</span><p class="text-sm">{{ m.specification.mode }} · {{ m.specification.method.replaceAll('_', ' ') }}</p><details v-if="m.job_id"><summary>Native job reference</summary><code>{{ m.job_id }}</code></details></td><td class="p-3 whitespace-nowrap">{{ m.state }}</td><td class="p-3">{{ duration(m.estimate.total_seconds) }}</td><td class="p-3">{{ duration(m.estimate.outage_seconds) }}</td><td class="p-3"><p v-if="m.reason">{{ hold(m.reason) }}</p><p v-for="reason in m.estimate.holds" :key="reason">{{ hold(reason) }}</p></td></tr></tbody></table></div>
    <p class="text-sm">Estimates use measured results for each phase and concurrency level, with a 25% margin. A cold export includes the complete migration in its outage estimate.</p>
  </section>

  <template v-if="listing">
    <section class="my-6 space-y-2"><h2 class="text-xl font-semibold">Existing campaigns</h2><p v-if="!listing.items.length">No campaigns in this application and environment.</p><p v-for="c in listing.items" :key="c.id"><Link :href="`${base}/${c.id}`" class="underline">{{ c.name }}</Link> · {{ c.state }}</p><p v-if="listing.limit_reached">Showing the latest 100 campaigns. Older campaigns remain available through their saved links.</p></section>
    <form class="space-y-6" @submit.prevent="create">
      <fieldset :disabled="disabled" class="space-y-5"><legend class="text-xl font-semibold">Create a migration campaign</legend>
        <label>Campaign name<input v-model="name" required maxlength="120" /></label>
        <div class="rounded border p-4 space-y-3"><h3 class="font-semibold">Reviewed plans</h3><p>Add complete operational migration plans from this application and environment. Preparation-only plans remain held.</p><label>Reviewed plan reference<input v-model="planId" maxlength="36" /></label><button type="button" @click="addPlan">Load reviewed plan</button>
          <section v-for="(m, index) in members" :key="m.id" class="rounded border p-4 space-y-2"><h4 class="font-semibold">Migration {{ index + 1 }} · {{ m.mode }}</h4><p class="break-all text-sm">{{ m.plan_id }}</p><label>Independent approval reference<input v-model="m.approval_id" required maxlength="36" /></label><label>Priority (higher starts first)<input v-model.number="m.priority" type="number" min="0" max="100" /></label><label>Shared outage group (optional)<input v-model="m.outage_group" placeholder="Group reference" maxlength="36" /></label><p class="text-sm">Members of the same group cannot migrate together.</p><label>Wait for completed migrations<select v-model="m.depends_on" multiple><option v-for="(other, j) in members.filter(v => v.id !== m.id)" :key="other.id" :value="other.id">{{ other.plan_id }} ({{ j + 1 }})</option></select></label><button type="button" @click="members = members.filter(v => v.id !== m.id)">Remove plan</button></section>
        </div>
        <label>Display time zone<input v-model="zone" required maxlength="100" /></label>
        <p>Enter all windows below in UTC. Saved schedules also display them in your selected time zone.</p>
        <section v-for="(rows, label) in { 'Migration windows': windows, 'Cutover windows': cutovers, 'Blackouts': blackouts }" :key="label" class="rounded border p-4"><h3 class="font-semibold">{{ label }}</h3><div v-for="(w, i) in rows" :key="i" class="grid gap-3 md:grid-cols-3"><label>Start (UTC)<input v-model="w.start" type="datetime-local" required /></label><label>End (UTC)<input v-model="w.end" type="datetime-local" required /></label><button v-if="rows.length > 1 || label === 'Blackouts'" type="button" @click="rows.splice(i, 1)">Remove window</button></div><button type="button" :disabled="rows.length >= 128" @click="rows.push({ start: stamp(1), end: stamp(7) })">Add window</button></section>
        <div class="grid gap-4 md:grid-cols-3"><label>Maximum active migrations<input v-model.number="maxActive" type="number" min="1" max="1000" required /></label><label>Stagger starts by (seconds)<input v-model.number="stagger" type="number" min="0" max="86400" required /></label><label>Stop new starts after held migrations<input v-model.number="failureLimit" type="number" min="1" max="1000" required /></label></div>
        <fieldset><legend class="font-semibold">Maximum concurrent work per phase</legend><p>Each concurrency level must have current measurements before admission.</p><div class="grid gap-4 md:grid-cols-3"><label v-for="phase in phases" :key="phase">{{ phase }}<input v-model.number="phaseLimits[phase]" type="number" min="1" max="1000" required /></label></div></fieldset>
        <button type="submit" :disabled="!members.length">Create draft campaign</button>
      </fieldset>
    </form>
  </template>
</CatalogueLayout>
</template>
