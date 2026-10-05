<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { Link, useForm } from '@inertiajs/vue3';
import IdentityLayout from '../../shared/ui/IdentityLayout.vue';

type Member = { id: string; subject: string; role: string; state: string; revision: number; site_id: string | null; environment: string | null; expires_at: string | null };
type Entitlement = { vcpu: number; memory_mib: number; storage_gib: number; workloads: number };
const props = defineProps<{
  tenant: { id: string; name: string; state: string; revision: number }; membership: { role: string; site_id: string | null; environment: string | null };
  canAdminister: boolean; memberships: Member[]; quota: { revision: number; entitlement: Entitlement | null } | null; notice: string | null;
  notificationCursor: string | null; notificationsAvailable: boolean;
  nextCursor: string | null; continued: boolean;
}>();
const member = useForm({ revision: 0, subject: '', role: 'reader', state: 'active', site_id: null as string | null, environment: null as string | null, expires_at: null as string | null, command_key: crypto.randomUUID() });
const quota = useForm({ revision: props.quota?.revision ?? 0, entitlement: props.quota?.entitlement ?? { vcpu: 0, memory_mib: 0, storage_gib: 0, workloads: 0 }, command_key: crypto.randomUUID() });
const state = useForm({ revision: props.tenant.revision, state: 'suspended', command_key: crypto.randomUUID() });
const errors = computed(() => [...Object.values(member.errors), ...Object.values(quota.errors), ...Object.values(state.errors)]);
const changed = ref(false);
const unavailable = ref(!props.notificationsAvailable);
const dirty = computed(() => member.isDirty || quota.isDirty || state.isDirty);
const viewedTenant = props.tenant.id;
let active = true;
let delay = 15_000;
let timer: ReturnType<typeof setTimeout> | undefined;
let request: AbortController | undefined;
const schedule = () => {
  clearTimeout(timer);
  if (active && props.canAdminister && document.visibilityState === 'visible') timer = setTimeout(poll, delay);
};
const poll = async () => {
  if (!active || props.tenant.id !== viewedTenant || document.visibilityState !== 'visible') return;
  const controller = new AbortController();
  request = controller;
  const deadline = setTimeout(() => controller.abort(), 10_000);
  try {
    const response = await fetch('/tenants/' + viewedTenant + '/notification-status', {
      credentials: 'same-origin', cache: 'no-store', redirect: 'manual', headers: { Accept: 'application/json' }, signal: controller.signal,
    });
    if (!active || props.tenant.id !== viewedTenant || document.visibilityState !== 'visible') return;
    if (response.type === 'opaqueredirect' || [401, 403, 404].includes(response.status)) {
      active = false;
      window.location.assign('/account');
      return;
    }
    if (!response.ok || !response.headers.get('Content-Type')?.includes('application/json')) throw new Error('unavailable');
    const value: unknown = await response.json();
    if (!active || props.tenant.id !== viewedTenant || document.visibilityState !== 'visible') return;
    if (!value || typeof value !== 'object' || !('cursor' in value)
        || !(value.cursor === null || (typeof value.cursor === 'string' && /^[0-9a-f-]{36}$/.test(value.cursor)))) throw new Error('unavailable');
    changed.value ||= !props.notificationsAvailable || value.cursor !== props.notificationCursor;
    unavailable.value = false;
    delay = 15_000;
  } catch {
    if (active && props.tenant.id === viewedTenant && document.visibilityState === 'visible') {
      unavailable.value = true;
      delay = Math.min(delay * 2, 120_000);
    }
  } finally {
    clearTimeout(deadline);
    request = undefined;
    schedule();
  }
};
const visibility = () => {
  clearTimeout(timer);
  if (document.visibilityState === 'hidden') request?.abort();
  else if (!request) schedule();
};
const refresh = () => window.location.assign('/tenants/' + viewedTenant);
onMounted(() => { document.addEventListener('visibilitychange', visibility); schedule(); });
onUnmounted(() => {
  active = false;
  clearTimeout(timer);
  request?.abort();
  document.removeEventListener('visibilitychange', visibility);
});
const edit = (value: Member) => {
  member.revision = value.revision; member.subject = value.subject; member.role = value.role; member.state = value.state;
  member.site_id = value.site_id; member.environment = value.environment; member.expires_at = value.expires_at; member.command_key = crypto.randomUUID();
  document.querySelector<HTMLInputElement>('#member-subject')?.focus();
};
</script>
<template>
  <IdentityLayout :title="tenant.name" description="Tenant membership and entitlement settings.">
    <Link href="/account" class="mt-5 inline-block text-teal-800 underline">All your tenants</Link>
    <p class="mt-3 text-sm text-slate-600">Your role: {{ membership.role.replaceAll('_', ' ') }}<span v-if="membership.site_id"> · {{ membership.site_id }}</span><span v-if="membership.environment"> · {{ membership.environment }}</span></p>
    <p v-if="notice" role="status" class="mt-4 text-sm text-teal-800">{{ notice }}</p>
    <div v-if="errors.length" role="alert" tabindex="-1"><p v-for="error in errors" :key="error">{{ error }}</p></div>
    <template v-if="canAdminister">
      <div v-if="changed || unavailable" role="status" class="mt-5 rounded-lg border border-teal-700 bg-teal-50 p-4">
        <p>{{ changed ? 'Tenant settings changed. Review the current values before saving.' : 'Change notifications are temporarily unavailable. You can refresh to review the current values.' }}</p>
        <p v-if="dirty" class="mt-2 text-sm">Your unsaved edits are still here. Refreshing will discard them.</p>
        <button type="button" @click="refresh">{{ dirty ? 'Discard edits and refresh' : 'Review current values' }}</button>
      </div>
      <h2 class="mt-7 text-xl font-semibold">Memberships</h2>
      <ul class="mt-3 space-y-3">
        <li v-for="item in memberships" :key="item.id" class="rounded-lg border border-slate-200 p-3">
          <p class="break-all font-medium">{{ item.subject }}</p>
          <p class="text-sm text-slate-600">{{ item.role.replaceAll('_', ' ') }} · {{ item.state }} · revision {{ item.revision }}</p>
          <button type="button" @click="edit(item)">Edit membership</button>
        </li>
      </ul>
      <p v-if="continued && !memberships.length" class="mt-3">No further memberships on this page.</p>
      <nav v-if="continued || nextCursor" class="mt-5 flex flex-wrap gap-5" aria-label="Membership pages">
        <p v-if="dirty" class="w-full text-sm">Changing pages will discard your unsaved edits.</p>
        <Link v-if="continued" :href="'/tenants/' + tenant.id" class="text-teal-800 underline">{{ dirty ? 'Discard edits and open first membership page' : 'First membership page' }}</Link>
        <Link v-if="nextCursor" :href="'/tenants/' + tenant.id + '?cursor=' + encodeURIComponent(nextCursor)" class="text-teal-800 underline">{{ dirty ? 'Discard edits and open next membership page' : 'Next membership page' }}</Link>
      </nav>
      <form @submit.prevent="member.post('/tenants/' + tenant.id + '/memberships', { preserveState: false })">
        <label for="member-subject">Member subject</label><input id="member-subject" v-model="member.subject" required maxlength="255" />
        <label for="member-role">Role</label>
        <select id="member-role" v-model="member.role" class="mt-2 min-h-11 w-full rounded-lg border border-slate-500 p-3">
          <option value="reader">Reader</option><option value="author">Author</option><option value="reviewer">Reviewer</option><option value="operator">Operator</option><option value="tenant_admin">Tenant administrator</option>
        </select>
        <label for="member-state">Membership state</label>
        <select id="member-state" v-model="member.state" class="mt-2 min-h-11 w-full rounded-lg border border-slate-500 p-3"><option value="active">Active</option><option value="revoked">Revoked</option></select>
        <label for="member-site">Site scope (optional)</label><input id="member-site" v-model="member.site_id" maxlength="64" />
        <label for="member-environment">Environment scope (optional)</label><input id="member-environment" v-model="member.environment" maxlength="64" />
        <label for="member-expiry">Expiry (optional, ISO 8601)</label><input id="member-expiry" v-model="member.expires_at" maxlength="64" placeholder="2026-12-31T23:59:00Z" />
        <p class="mt-2 text-sm text-slate-600">Changes invalidate grants and approvals tied to the previous membership revision.</p>
        <button type="submit" :disabled="member.processing">{{ member.revision ? 'Update membership' : 'Add membership' }}</button>
      </form>
      <form @submit.prevent="quota.post('/tenants/' + tenant.id + '/quota', { preserveState: false })">
        <h2 class="text-xl font-semibold">Quota entitlement</h2>
        <p class="mt-2 text-sm text-slate-600">These limits are allocations. Observed capacity and reservations are maintained separately.</p>
        <label for="quota-cpu">vCPU</label><input id="quota-cpu" v-model.number="quota.entitlement.vcpu" type="number" min="0" max="1000000000" required />
        <label for="quota-memory">Memory (MiB)</label><input id="quota-memory" v-model.number="quota.entitlement.memory_mib" type="number" min="0" max="1000000000" required />
        <label for="quota-storage">Storage (GiB)</label><input id="quota-storage" v-model.number="quota.entitlement.storage_gib" type="number" min="0" max="1000000000" required />
        <label for="quota-workloads">Workloads</label><input id="quota-workloads" v-model.number="quota.entitlement.workloads" type="number" min="0" max="1000000000" required />
        <button type="submit" :disabled="quota.processing">Save quota</button>
      </form>
      <button type="button" :disabled="state.processing" @click="state.post('/tenants/' + tenant.id + '/state', { preserveState: false })">Suspend tenant access</button>
    </template>
    <Link href="/logout" method="post" as="button">Sign out</Link>
  </IdentityLayout>
</template>
