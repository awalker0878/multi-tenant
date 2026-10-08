<script setup lang="ts">
import { computed, ref } from 'vue';
import { useForm } from '@inertiajs/vue3';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';
const props=defineProps<{tenantId:string;base:string;planId:string;digest:string}>();
const form=useForm({command_key:crypto.randomUUID() as string,plan_id:props.planId,plan_digest:props.digest,approval_id:'',campaign_id:''});
const errorMessage=computed(()=>(form.errors as Record<string,string>).command);
const uncertain=ref(false);
function submit(){form.post(props.base,{onError:errors=>{uncertain.value=errors.command_status==='503';}});}
</script>
<template>
<CatalogueLayout title="Run a simulation" :tenant-id="tenantId">
  <p class="max-w-2xl text-slate-700">This run uses an isolated simulation campaign. It cannot change a native platform or establish production support.</p>
  <form class="mt-6 max-w-2xl space-y-5" @submit.prevent="submit">
    <p>Selected plan: <strong class="break-all">{{ planId }}</strong></p>
    <label class="block">Approval reference<input v-model="form.approval_id" :disabled="uncertain || form.processing" required class="mt-1 block w-full rounded border p-2" /></label>
    <label class="block">Isolated campaign reference<input v-model="form.campaign_id" :disabled="uncertain || form.processing" required class="mt-1 block w-full rounded border p-2" /></label>
    <p v-if="errorMessage" role="alert" class="rounded border border-amber-600 bg-amber-50 p-3">{{ errorMessage }}</p>
    <p v-if="uncertain" role="status">The admission response was lost. Retry this same request to recover its receipt; it will not create another logical job.</p>
    <button type="submit" :disabled="form.processing" class="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-50">{{ uncertain?'Recover admission receipt':'Admit simulation' }}</button>
  </form>
</CatalogueLayout>
</template>
