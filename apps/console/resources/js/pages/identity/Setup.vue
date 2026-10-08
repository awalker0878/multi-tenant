<script setup lang="ts">
import { computed, ref } from 'vue';
import { Link, useForm } from '@inertiajs/vue3';
import IdentityLayout from '../../shared/ui/IdentityLayout.vue';
import ChangeNotice from '../../shared/ui/ChangeNotice.vue';

const props = defineProps<{
  settings: { issuer: string; client_id: string; administrator_subject: string; private_networks: string[]; secret_configured: boolean } | null;
  notificationCursor: string | null; notificationsAvailable: boolean;
  revision: number; activeRevision: number | null; callbackUrl: string; verified: boolean; notice: string | null; federated: boolean;
}>();
const networks = ref(props.settings?.private_networks.join(', ') ?? '');
const form = useForm({
  revision: props.revision, issuer: props.settings?.issuer ?? '', client_id: props.settings?.client_id ?? '',
  client_secret: '', administrator_subject: props.settings?.administrator_subject ?? '', private_networks: [] as string[],
});
const request = useForm({});
const dirty = computed(() => form.isDirty || networks.value !== (props.settings?.private_networks.join(', ') ?? ''));
const errors = computed(() => Object.values(form.errors).concat(Object.values(request.errors)));
const save = () => {
  form.private_networks = networks.value.split(',').map(value => value.trim()).filter(Boolean);
  form.put('/setup', { preserveState: false, onFinish: () => form.reset('client_secret') });
};
</script>

<template>
  <IdentityLayout title="Installation setup" :description="federated ? 'Manage your installation’s external identity provider.' : 'You are signed in as the local administrator.'">
    <p v-if="!federated" class="mt-5 text-sm text-teal-800">Administrator password: <span>Changed</span></p>
    <p class="mt-4 font-semibold">External single sign-on: {{ activeRevision ? 'Active' : (settings ? 'Awaiting verification' : 'Not configured') }}</p>
    <p v-if="notice" role="status" class="mt-4 rounded-lg bg-teal-50 p-3 text-sm">{{ notice }}</p>
    <div v-if="errors.length" role="alert" tabindex="-1"><p v-for="error in errors" :key="error">{{ error }}</p></div>
    <p class="mt-4 text-sm leading-6 text-slate-700">Register this callback URL with your provider:</p>
    <p class="mt-1 break-all rounded-lg bg-slate-100 p-3 text-sm">{{ callbackUrl }}</p>
    <ChangeNotice endpoint="/setup/notification-status" refresh-url="/setup" authority-loss-url="/setup"
      changed-message="Identity provider settings changed. Review the current values before saving." :notification-cursor="notificationCursor" :notifications-available="notificationsAvailable" :dirty="dirty" :enabled="true" />
    <form @submit.prevent="save">
      <label for="issuer">Issuer URL</label>
      <input id="issuer" v-model="form.issuer" type="url" required maxlength="2048" placeholder="https://identity.example.ca/realms/hosting" />
      <label for="client">Client ID</label>
      <input id="client" v-model="form.client_id" required maxlength="255" autocomplete="off" />
      <label for="client-secret">Client secret</label>
      <input id="client-secret" v-model="form.client_secret" type="password" :required="!settings" maxlength="4096" autocomplete="new-password" aria-describedby="secret-help" />
      <p id="secret-help" class="mt-2 text-sm text-slate-600">{{ settings ? 'Leave blank to retain the secret for the same issuer and client.' : 'The secret is stored securely and is never displayed again.' }}</p>
      <label for="administrator">Federated administrator subject</label>
      <input id="administrator" v-model="form.administrator_subject" required maxlength="255" autocomplete="off" aria-describedby="subject-help" />
      <p id="subject-help" class="mt-2 text-sm text-slate-600">Use the administrator’s exact, stable OIDC subject (sub). An email address or group name does not grant authority.</p>
      <label for="networks">Private provider networks (optional)</label>
      <input id="networks" v-model="networks" maxlength="1024" placeholder="10.40.80.0/22" aria-describedby="networks-help" />
      <p id="networks-help" class="mt-2 text-sm text-slate-600">Comma-separated private IPv4 ranges permitted for your enterprise identity provider.</p>
      <button type="submit" :disabled="form.processing">Save provider settings</button>
    </form>
    <div v-if="settings" class="mt-5 border-t border-slate-200 pt-2">
      <button type="button" :disabled="request.processing || dirty" @click="request.post('/setup/test')">Test administrator sign-in</button>
      <p class="mt-3 text-sm leading-6 text-slate-700">Sign in with the named federated administrator to verify the saved settings. Activation retires all local sessions. Updated settings leave active single sign-on available until verification succeeds.</p>
      <button v-if="verified" type="button" :disabled="request.processing || dirty" @click="request.post('/setup/activate')">Activate single sign-on</button>
    </div>
    <nav class="mt-6 flex flex-wrap items-baseline justify-between gap-4" aria-label="Account">
      <Link v-if="!federated" href="/password" class="text-teal-800 underline">Change password</Link>
      <Link v-if="federated" href="/account" class="text-teal-800 underline">Your tenants</Link>
      <Link href="/logout" method="post" as="button">Sign out</Link>
    </nav>
  </IdentityLayout>
</template>
