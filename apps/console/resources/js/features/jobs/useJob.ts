import { onMounted, onUnmounted, ref } from 'vue';
import { router } from '@inertiajs/vue3';
import type { Job } from './contracts';

export function useJob(endpoint:string, initial:Job, custodyEndpoint?:string) {
  const job=ref<Job|null>(initial), unavailable=ref(false), now=ref(Date.now()/1000);
  let active=true, running=false, delay=5000;
  let timer:ReturnType<typeof setTimeout>|undefined, clock:ReturnType<typeof setInterval>|undefined, controller:AbortController|undefined;
  const poll=async()=>{
    if(!active || running || document.hidden)return;
    clearTimeout(timer);running=true;controller=new AbortController();
    const deadline=setTimeout(()=>controller?.abort(),12000);
    try{
      const response=await fetch(endpoint,{headers:{Accept:'application/json'},credentials:'same-origin',cache:'no-store',redirect:'manual',signal:controller.signal});
      if(!active)return;
      if(response.type==='opaqueredirect' || [401,403,404].includes(response.status)){
        job.value=null;active=false;router.cancelAll();router.clearHistory();window.location.replace('/account');return;
      }
      if(custodyEndpoint){
        const custody=await fetch(custodyEndpoint,{headers:{Accept:'application/json'},credentials:'same-origin',cache:'no-store',redirect:'manual',signal:controller.signal});
        if(custody.type==='opaqueredirect' || [401,403,404].includes(custody.status)){
          job.value=null;unavailable.value=true;active=false;router.clearHistory();window.location.replace('/account');return;
        }
        if(!custody.ok)throw new Error();
        await custody.json();
      }
      if(!response.ok || !response.headers.get('Content-Type')?.includes('application/json'))throw new Error();
      const next=await response.json() as Job;
      if(next.id!==initial.id || next.tenant_id!==initial.tenant_id || next.simulation!==true || (job.value && next.revision<job.value.revision))throw new Error();
      job.value=next;unavailable.value=false;delay=5000;
    }catch{if(active){unavailable.value=true;delay=Math.min(delay*2,60000);}}
    finally{running=false;clearTimeout(deadline);if(active)timer=setTimeout(poll,delay);}
  };
  const reconnect=()=>{if(!document.hidden)void poll();};
  const hide=()=>{job.value=null;unavailable.value=true;controller?.abort();};
  const show=(event:PageTransitionEvent)=>{if(event.persisted){job.value=null;void poll();}};
  onMounted(()=>{timer=setTimeout(poll,delay);clock=setInterval(()=>{now.value=Date.now()/1000;},1000);window.addEventListener('online',reconnect);document.addEventListener('visibilitychange',reconnect);window.addEventListener('pagehide',hide);window.addEventListener('pageshow',show);});
  onUnmounted(()=>{active=false;clearTimeout(timer);clearInterval(clock);controller?.abort();window.removeEventListener('online',reconnect);document.removeEventListener('visibilitychange',reconnect);window.removeEventListener('pagehide',hide);window.removeEventListener('pageshow',show);});
  return {job,unavailable,now,poll};
}
