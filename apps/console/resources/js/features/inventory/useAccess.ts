import { onMounted, onUnmounted, ref } from 'vue';
import { router } from '@inertiajs/vue3';

export function useInventoryAccess(endpoint: string) {
  const now = ref(Date.now() / 1000);
  const unavailable = ref(false);
  let active = true;
  let pollTimer: ReturnType<typeof setTimeout> | undefined;
  let clock: ReturnType<typeof setInterval> | undefined;
  let controller: AbortController | undefined;
  let delay = 15_000;
  const poll = async () => {
    if (!active) return;
    if (document.hidden) { pollTimer = setTimeout(poll, delay); return; }
    controller = new AbortController();
    const deadline = setTimeout(() => controller?.abort(), 8_000);
    try {
      const response = await fetch(endpoint, { headers: { Accept: 'application/json' }, credentials: 'same-origin', cache: 'no-store', redirect: 'manual', signal: controller.signal });
      if (!active) return;
      if (response.type === 'opaqueredirect' || [401, 403, 404].includes(response.status)) {
        active = false; router.cancelAll(); router.clearHistory(); window.location.replace('/account'); return;
      }
      if (!response.ok || !response.headers.get('Content-Type')?.includes('application/json')) throw new Error('unavailable');
      const value: unknown = await response.json();
      if (!value || typeof value !== 'object' || !('available' in value) || value.available !== true) throw new Error('unavailable');
      unavailable.value = false; delay = 15_000;
    } catch { if (active) { unavailable.value = true; delay = Math.min(delay * 2, 120_000); } }
    finally { clearTimeout(deadline); if (active) pollTimer = setTimeout(poll, delay); }
  };
  onMounted(() => { clock = setInterval(() => { now.value = Date.now() / 1000; }, 1_000); pollTimer = setTimeout(poll, delay); });
  onUnmounted(() => { active = false; clearTimeout(pollTimer); clearInterval(clock); controller?.abort(); });
  return { now, unavailable };
}

export const observedTime = (value: number | null) => value === null ? 'Not observed' : new Date(value * 1000).toLocaleString();
