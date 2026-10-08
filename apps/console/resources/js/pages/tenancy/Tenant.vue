<script setup lang="ts">
import { computed } from 'vue';
import { Link, useForm } from '@inertiajs/vue3';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';
import ChangeNotice from '../../shared/ui/ChangeNotice.vue';

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
const dirty = computed(() => member.isDirty || quota.isDirty || state.isDirty);
const edit = (value: Member) => {
  member.revision = value.revision; member.subject = value.subject; member.role = value.role; member.state = value.state;
  member.site_id = value.site_id; member.environment = value.environment; member.expires_at = value.expires_at; member.command_key = crypto.randomUUID();
  document.querySelector<HTMLInputElement>('#member-subject')?.focus();
};
</script>
<template>
  <CatalogueLayout :title="tenant.name" :tenant-id="tenant.id">
    <p class="text-sm text-slate-600">Tenant membership and entitlement settings.</p>
    <Link href="/account" class="mt-5 inline-block text-teal-800 underline">All your tenants</Link>
    <nav class="mt-4 flex flex-wrap gap-4" aria-label="Tenant workspaces"><Link :href="`/tenants/${tenant.id}/applications${membership.environment ? '?environment=' + encodeURIComponent(membership.environment) : ''}`" class="text-teal-800 underline">Application catalogue</Link><Link :href="`/tenants/${tenant.id}/catalogue-references`" class="text-teal-800 underline">Environments and domains</Link><Link :href="`/tenants/${tenant.id}/inventory${membership.site_id ? '/sites/' + membership.site_id : ''}`" class="text-teal-800 underline">Observed inventory</Link></nav>
    <p class="mt-3 text-sm text-slate-600">Your role: {{ membership.role.replaceAll('_', ' ') }}<span v-if="membership.site_id"> · {{ membership.site_id }}</span><span v-if="membership.environment"> · {{ membership.environment }}</span></p>
    <p v-if="notice" role="status" class="mt-4 text-sm text-teal-800">{{ notice }}</p>
    <div v-if="errors.length" role="alert" tabindex="-1"><p v-for="error in errors" :key="error">{{ error }}</p></div>
    <template v-if="canAdminister">
      <ChangeNotice :key="tenant.id" :endpoint="'/tenants/' + tenant.id + '/notification-status'" :refresh-url="'/tenants/' + tenant.id" authority-loss-url="/account"
        changed-message="Tenant settings changed. Review the current values before saving." :notification-cursor="notificationCursor" :notifications-available="notificationsAvailable" :dirty="dirty" :enabled="canAdminister" />
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
  </CatalogueLayout>
</template>
