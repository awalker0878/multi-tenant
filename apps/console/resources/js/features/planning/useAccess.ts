import { onMounted, onUnmounted, ref } from 'vue';
import { router } from '@inertiajs/vue3';
import type { Validity } from './contracts';

export function usePlanningAccess(endpoint: string | null, initial?: Validity) {
  const validity = ref(initial);
  const now = ref(Date.now()/1000);
  const unavailable = ref(false);
  let active=true;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let clock: ReturnType<typeof setInterval> | undefined;
  let controller: AbortController | undefined;
  let delay=15_000;
  const poll=async () => {
    if (!active || !endpoint) return;
    controller=new AbortController();
    const deadline=setTimeout(()=>controller?.abort(),12_000);
    try {
      const response=await fetch(endpoint,{headers:{Accept:'application/json'},credentials:'same-origin',cache:'no-store',redirect:'manual',signal:controller.signal});
      if (!active) return;
      if (response.type==='opaqueredirect' || [401,403,404].includes(response.status)) {
        active=false;router.cancelAll();router.clearHistory();window.location.replace('/account');return;
      }
      if (!response.ok || !response.headers.get('Content-Type')?.includes('application/json')) throw new Error();
      const result=await response.json() as {available:boolean;validity:Validity|null};
      if (!result.available) throw new Error();
      validity.value=result.validity ?? undefined;unavailable.value=false;delay=15_000;
    } catch { if(active){unavailable.value=true;delay=Math.min(delay*2,120_000);} }
    finally {clearTimeout(deadline);if(active)timer=setTimeout(poll,delay);}
  };
  onMounted(()=>{clock=setInterval(()=>{now.value=Date.now()/1000;},1000);if(endpoint)timer=setTimeout(poll,delay);});
  onUnmounted(()=>{active=false;clearTimeout(timer);clearInterval(clock);controller?.abort();});
  return {validity,now,unavailable};
}
