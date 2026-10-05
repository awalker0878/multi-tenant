<script setup lang="ts">
import { Link, useForm } from '@inertiajs/vue3';
import IdentityLayout from '../../shared/ui/IdentityLayout.vue';

const form = useForm({ current_password: '', password: '', password_confirmation: '' });
const submit = () => form.post('/password', { onFinish: () => form.reset() });
</script>

<template>
  <IdentityLayout title="Change your password" description="Before continuing with setup, replace the temporary password with a different password of at least 15 characters.">
    <form @submit.prevent="submit">
      <label for="current-password">Current password</label>
      <input id="current-password" v-model="form.current_password" name="current_password" type="password" autocomplete="current-password" required maxlength="512" :aria-invalid="!!form.errors.current_password" aria-describedby="current-error" />
      <p v-if="form.errors.current_password" id="current-error" role="alert">{{ form.errors.current_password }}</p>
      <label for="new-password">New password</label>
      <input id="new-password" v-model="form.password" name="password" type="password" autocomplete="new-password" required minlength="15" maxlength="128" :aria-invalid="!!form.errors.password" aria-describedby="password-error" />
      <p v-if="form.errors.password" id="password-error" role="alert">{{ form.errors.password }}</p>
      <label for="confirm-password">Confirm new password</label>
      <input id="confirm-password" v-model="form.password_confirmation" name="password_confirmation" type="password" autocomplete="new-password" required minlength="15" maxlength="128" />
      <button type="submit" :disabled="form.processing">{{ form.processing ? 'Saving…' : 'Change password' }}</button>
    </form>
    <Link href="/logout" method="post" as="button">Sign out</Link>
  </IdentityLayout>
</template>
