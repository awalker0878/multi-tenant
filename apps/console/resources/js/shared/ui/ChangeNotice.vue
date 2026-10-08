<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';

const props = defineProps<{
  endpoint: string; refreshUrl: string; authorityLossUrl: string; changedMessage: string;
  notificationCursor: string | null; notificationsAvailable: boolean; dirty: boolean; enabled: boolean;
}>();
const changed = ref(false);
const unavailable = ref(!props.notificationsAvailable);
const endpoint = props.endpoint;
let active = true;
let delay = 15_000;
let timer: ReturnType<typeof setTimeout> | undefined;
let request: AbortController | undefined;
const schedule = () => {
  clearTimeout(timer);
  if (active && props.enabled && document.visibilityState === 'visible') timer = setTimeout(poll, delay);
};
const poll = async () => {
  if (!active || props.endpoint !== endpoint || document.visibilityState !== 'visible') return;
  const controller = new AbortController();
  request = controller;
  const deadline = setTimeout(() => controller.abort(), 10_000);
  try {
    const response = await fetch(endpoint, {
      credentials: 'same-origin', cache: 'no-store', redirect: 'manual', headers: { Accept: 'application/json' }, signal: controller.signal,
    });
    if (!active || props.endpoint !== endpoint || document.visibilityState !== 'visible') return;
    if (response.type === 'opaqueredirect' || [401, 403, 404].includes(response.status)) {
      active = false;
      window.location.assign(props.authorityLossUrl);
      return;
    }
    if (!response.ok || !response.headers.get('Content-Type')?.includes('application/json')) throw new Error('unavailable');
    const value: unknown = await response.json();
    if (!active || props.endpoint !== endpoint || document.visibilityState !== 'visible') return;
    if (!value || typeof value !== 'object' || !('cursor' in value)
        || !(value.cursor === null || (typeof value.cursor === 'string' && /^[0-9a-f-]{36}$/.test(value.cursor)))) throw new Error('unavailable');
    changed.value ||= !props.notificationsAvailable || value.cursor !== props.notificationCursor;
    unavailable.value = false;
    delay = 15_000;
  } catch {
    if (active && props.endpoint === endpoint && document.visibilityState === 'visible') {
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
const refresh = () => window.location.assign(props.refreshUrl);
onMounted(() => { document.addEventListener('visibilitychange', visibility); schedule(); });
onUnmounted(() => {
  active = false;
  clearTimeout(timer);
  request?.abort();
  document.removeEventListener('visibilitychange', visibility);
});
</script>
<template>
    <div v-if="changed || unavailable" role="status" class="mt-5 rounded-lg border border-teal-700 bg-teal-50 p-4">
      <p>{{ changed ? changedMessage : 'Change notifications are temporarily unavailable. You can refresh to review the current values.' }}</p>
      <p v-if="dirty" class="mt-2 text-sm">Your unsaved edits are still here. Refreshing will discard them.</p>
      <button type="button" @click="refresh">{{ dirty ? 'Discard edits and refresh' : 'Review current values' }}</button>
    </div>
</template>
