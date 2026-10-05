<script setup lang="ts">
import { Link } from '@inertiajs/vue3';
import IdentityLayout from '../../shared/ui/IdentityLayout.vue';
</script>

<template>
  <IdentityLayout title="Installation setup" description="You are signed in as the local administrator.">
    <dl class="mt-7 space-y-5">
      <div><dt class="font-semibold text-slate-950">Administrator password</dt><dd class="mt-1 text-teal-800">Changed</dd></div>
      <div><dt class="font-semibold text-slate-950">External single sign-on</dt><dd class="mt-1 text-slate-700">Not configured</dd></div>
    </dl>
    <p class="mt-6 text-sm leading-6 text-slate-700">The local account is available until an external administrator completes verified sign-in and handover.</p>
    <div class="mt-5 flex items-baseline justify-between gap-4">
      <Link href="/password" class="font-medium text-teal-800 underline">Change password</Link>
      <Link href="/logout" method="post" as="button">Sign out</Link>
    </div>
  </IdentityLayout>
</template>
