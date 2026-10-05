<script setup lang="ts">
import { computed } from 'vue';
import { Link, useForm } from '@inertiajs/vue3';
import IdentityLayout from '../../shared/ui/IdentityLayout.vue';

defineProps<{ tenants: { id: string; name: string; state: string; role: string; revision: number }[]; canCreate: boolean; notice: string | null }>();
const create = useForm({ name: '', administrator_subject: '', command_key: crypto.randomUUID() });
const state = useForm({ revision: 0, state: 'active', command_key: crypto.randomUUID() });
const errors = computed(() => Object.values(create.errors).concat(Object.values(state.errors)));
const activate = (id: string, revision: number) => {
  state.revision = revision;
  state.post('/tenants/' + id + '/state', { preserveState: false });
};
</script>
<template>
  <IdentityLayout title="Your tenants" description="Choose a tenant from your current memberships.">
    <p v-if="notice" role="status" class="mt-5 text-sm text-teal-800">{{ notice }}</p>
    <div v-if="errors.length" role="alert" tabindex="-1"><p v-for="error in errors" :key="error">{{ error }}</p></div>
    <p v-if="!tenants.length" class="mt-6 text-slate-700">You have no current tenant memberships. Contact your tenant administrator.</p>
    <ul v-else class="mt-6 space-y-3">
      <li v-for="tenant in tenants" :key="tenant.id" class="rounded-lg border border-slate-200 p-4">
        <Link v-if="tenant.state === 'active'" :href="'/tenants/' + tenant.id" class="font-semibold text-teal-800 underline">{{ tenant.name }}</Link>
        <span v-else class="font-semibold">{{ tenant.name }}</span>
        <p class="mt-1 text-sm text-slate-600">{{ tenant.role.replaceAll('_', ' ') }} · {{ tenant.state }}</p>
        <button v-if="tenant.state === 'suspended' && tenant.role === 'tenant_admin'" type="button" :disabled="state.processing" @click="activate(tenant.id, tenant.revision)">Reactivate tenant</button>
      </li>
    </ul>
    <form v-if="canCreate" @submit.prevent="create.post('/tenants', { preserveState: false })">
      <h2 class="text-xl font-semibold">Create a tenant</h2>
      <label for="tenant-name">Tenant name</label><input id="tenant-name" v-model="create.name" required maxlength="200" />
      <label for="tenant-admin">Initial administrator subject</label><input id="tenant-admin" v-model="create.administrator_subject" required maxlength="255" />
      <p class="mt-2 text-sm text-slate-600">Use the exact subject from the active provider. Installation administration does not automatically grant access to this tenant.</p>
      <button type="submit" :disabled="create.processing">Create tenant</button>
    </form>
    <nav class="mt-6 flex items-baseline justify-between gap-4" aria-label="Account">
      <Link v-if="canCreate" href="/setup" class="text-teal-800 underline">Identity provider</Link>
      <Link href="/logout" method="post" as="button">Sign out</Link>
    </nav>
  </IdentityLayout>
</template>
