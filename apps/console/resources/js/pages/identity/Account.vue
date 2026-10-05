<script setup lang="ts">
import { Link } from '@inertiajs/vue3';
import IdentityLayout from '../../shared/ui/IdentityLayout.vue';
</script>
<template>
  <IdentityLayout title="Your account" description="You are signed in through your external identity provider.">
    <p class="mt-5 text-slate-700">Tenant access is granted by your tenant administrator.</p>
    <Link href="/logout" method="post" as="button">Sign out</Link>
  </IdentityLayout>
</template>
