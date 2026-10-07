// Isolated E2 UI harness. No Governance, Inventory or native authority is issued.
import '../../resources/css/app.css';
import { createApp, h } from 'vue';
import { createInertiaApp } from '@inertiajs/vue3';
import Migration from '../../resources/js/pages/inventory/Migration.vue';

void createInertiaApp({
  page: JSON.parse(document.getElementById('app')!.dataset.page!),
  resolve: () => Migration,
  setup({ el, App, props, plugin }) { createApp({ render: () => h(App, props) }).use(plugin).mount(el); },
});
