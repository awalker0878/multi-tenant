// Isolated E2 UI harness. No Governance, Inventory or native authority is issued.
import '../../resources/css/app.css';
import { createApp, h, type DefineComponent } from 'vue';
import { createInertiaApp } from '@inertiajs/vue3';
import { resolvePageComponent } from 'laravel-vite-plugin/inertia-helpers';

void createInertiaApp({
  page: JSON.parse(document.getElementById('app')!.dataset.page!),
  resolve: name => resolvePageComponent<DefineComponent>(
    `../../resources/js/pages/${name}.vue`,
    import.meta.glob<DefineComponent>('../../resources/js/pages/**/*.vue'),
  ),
  setup({ el, App, props, plugin }) { createApp({ render: () => h(App, props) }).use(plugin).mount(el); },
});
