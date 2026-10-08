// Isolated E2 UI harness. No Governance, Inventory or native authority is issued.
import '../../resources/css/app.css';
import { createApp, h } from 'vue';
import { createInertiaApp } from '@inertiajs/vue3';
import OperatorInputs from '../../resources/js/pages/inventory/OperatorInputs.vue';
import Fleet from '../../resources/js/pages/inventory/Fleet.vue';
import Migration from '../../resources/js/pages/inventory/Migration.vue';
import NativeJob from '../../resources/js/pages/jobs/NativeJob.vue';
import Campaigns from '../../resources/js/pages/jobs/Campaigns.vue';

void createInertiaApp({
  page: JSON.parse(document.getElementById('app')!.dataset.page!),
  resolve: name => name === 'jobs/NativeJob' ? NativeJob : name === 'inventory/OperatorInputs' ? OperatorInputs : name === 'jobs/Campaigns' ? Campaigns : name === 'inventory/Fleet' ? Fleet : Migration,
  setup({ el, App, props, plugin }) { createApp({ render: () => h(App, props) }).use(plugin).mount(el); },
});
