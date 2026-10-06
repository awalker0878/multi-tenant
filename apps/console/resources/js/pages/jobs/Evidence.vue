<script setup lang="ts">
import { computed } from 'vue';
import { Link } from '@inertiajs/vue3';
import CatalogueLayout from '../../shared/ui/CatalogueLayout.vue';
import type { Observation } from '../../features/jobs/contracts';
import { useJob } from '../../features/jobs/useJob';
import type { Job } from '../../features/jobs/contracts';
const props=defineProps<{tenantId:string;jobUrl:string;job:Job;evidence:{id:string;job_id:string;digest:string;source_revision:string;retention_until:number;observations:Observation[];reviews:{id:string;decision:string;recorded_at:number}[]}}>();
// The same current-access monitor clears this view on revoked authority and BFCache restore.
const {unavailable,job,now}=useJob(`${props.jobUrl}/status`,props.job,`${props.jobUrl}/evidence/${props.evidence.id}/status`);
const stale=computed(()=>unavailable.value || !job.value || now.value-job.value.observed_at>20);
</script>
<template><CatalogueLayout title="Simulation evidence" :tenant-id="tenantId">
<p v-if="stale" role="alert">Current access is unavailable. Refresh before relying on this evidence.</p>
<div v-else><p class="rounded border border-indigo-300 bg-indigo-50 p-3">E2 isolated simulation evidence. This record does not qualify a native platform.</p>
<dl class="my-5 space-y-2"><dt>Custody reference</dt><dd class="break-all">{{evidence.id}}</dd><dt>SHA-256 digest</dt><dd class="break-all">{{evidence.digest}}</dd><dt>Execution source revision</dt><dd class="break-all">{{evidence.source_revision}}</dd><dt>Retained through</dt><dd>{{new Date(evidence.retention_until*1000).toLocaleDateString()}}</dd></dl>
<h2 class="text-lg font-semibold">Independently verified effects</h2><ol class="my-3 divide-y rounded border"><li v-for="observation in evidence.observations" :key="observation.operation_id" class="break-all p-3">{{observation.operation_id}} · {{observation.outcome.replaceAll('_',' ')}} · {{observation.effect_count}} observed effect</li></ol>
<h2 class="text-lg font-semibold">Review record</h2><p v-if="!evidence.reviews.length">Independent evidence review is pending.</p><ul v-else><li v-for="review in evidence.reviews" :key="review.id">{{review.decision.replaceAll('_',' ')}} · {{new Date(review.recorded_at*1000).toLocaleString()}}</li></ul></div>
<Link :href="jobUrl" class="my-5 inline-block underline">Back to job</Link>
</CatalogueLayout></template>
