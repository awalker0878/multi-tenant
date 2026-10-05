<script setup lang="ts">
import { useForm } from '@inertiajs/vue3';
import IdentityLayout from '../../shared/ui/IdentityLayout.vue';

const form = useForm({ username: 'admin', password: '' });
const federation = useForm({});
const submit = () => form.post('/login', { onFinish: () => form.reset('password') });
</script>

<template>
  <IdentityLayout title="Administrator sign-in" description="Use the local administrator account provided during deployment to set up this installation.">
    <form @submit.prevent="submit">
      <label for="username">Account</label>
      <input id="username" v-model="form.username" name="username" autocomplete="username" required maxlength="128" :aria-invalid="!!form.errors.username" aria-describedby="username-error" />
      <p v-if="form.errors.username" id="username-error" role="alert">{{ form.errors.username }}</p>
      <label for="password">Password</label>
      <input id="password" v-model="form.password" name="password" type="password" autocomplete="current-password" required maxlength="512" :aria-invalid="!!form.errors.password" aria-describedby="password-error" />
      <p v-if="form.errors.password" id="password-error" role="alert">{{ form.errors.password }}</p>
      <button type="submit" :disabled="form.processing">{{ form.processing ? 'Signing in…' : 'Sign in' }}</button>
    </form>
    <form @submit.prevent="federation.post('/identity/sign-in')">
      <button type="submit" :disabled="federation.processing">Sign in with your identity provider</button>
    </form>
  </IdentityLayout>
</template>
