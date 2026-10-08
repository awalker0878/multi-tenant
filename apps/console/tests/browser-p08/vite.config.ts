import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import tailwindcss from '@tailwindcss/vite';
import { readFileSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import { operatorFixture } from './operator-fixture.ts';
import { fleetFixture } from './fleet-fixture.ts';
import { campaignFixture } from './campaign-fixture.ts';

export const tenant = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
export const site = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
export const route = `/tenants/${tenant}/inventory/sites/${site}/migration`;
let state: any;
function reset(ahv = false) {
  const fixture = JSON.parse(readFileSync(`../../contracts/fixtures/inventory/${ahv ? 'ahv-destination-v1' : 'migration-profile-v1'}.json`, 'utf8'));
  const now = Math.floor(Date.now() / 1000);
  state = { posts: [], errors: {}, notice: null, uncertain: false, access: 200,
    workspace: { methods: ['VM_COLD_EXPORT', 'VM_SNAPSHOT_BASELINE_APP_DELTA'], owner_fields: Object.keys(fixture.review.owner_inputs), review: null,
      profiles: ['source', 'target'].map(side => ({ id: fixture.review[`${side}_profile_id`], endpoint_id: randomUUID(), generation_id: randomUUID(), native_id: side === 'source' ? 'vm-42 <img src=x onerror=alert(1)>' : 'project-a', profile_type: fixture[side].profile_type, digest: 'a'.repeat(64), current: true, expires_at: now + 300, collected_at: now, facts: { ...fixture[side], observed_at: now } })) } };
}
reset();
export default defineConfig({
  plugins: [vue(), tailwindcss(), fleetFixture(), campaignFixture(), operatorFixture(), { name: 'p08-isolated-observations', configureServer(server) {
    server.middlewares.use(async (req, res, next) => {
      const path = req.url?.split('?')[0];
      if (path !== route && path !== route + '/status' && path !== '/__fixture' && path !== '/account') return next();
      let body = '';
      for await (const chunk of req) { body += chunk; if (body.length > 65536) { res.statusCode = 413; res.end(); return; } }
      const send = (value: unknown, status = 200) => { res.statusCode = status; res.setHeader('Content-Type', 'application/json'); res.setHeader('Cache-Control', 'no-store'); res.end(JSON.stringify(value)); };
      if (path === '/__fixture') {
        if (req.method === 'POST') {
          const control = JSON.parse(body);
          if (control.reset) reset(!!control.ahv);
          if (control.uncertain) state.uncertain = true;
          if (control.access) state.access = control.access;
          if (control.expire) state.workspace.profiles.forEach((p: any) => { p.expires_at = Math.floor(Date.now()/1000) - 1; p.current = false; });
        }
        return send(state);
      }
      if (path === '/account') { res.setHeader('Content-Type', 'text/html'); res.end('<h1>Your tenants</h1>'); return; }
      if (path?.endsWith('/status')) return send({ available: true }, state.access);
      if (req.method === 'POST') {
        const command = JSON.parse(body); state.posts.push(command);
        if (command.operation === 'save') state.workspace.review = { revision: 1, digest: 'b'.repeat(64), input: command.review, source: state.workspace.profiles[0], target: state.workspace.profiles[1], holds: [], confirmed_by: null, confirmed_at: null, confirmation_current: false };
        else state.workspace.review.confirmation_current = true;
        state.errors = state.uncertain ? { inventory_status: '503', inventory: 'Outcome uncertain. Retry the unchanged command.' } : {};
        state.notice = state.uncertain ? null : command.operation === 'save' ? 'Migration review saved.' : 'Migration review confirmed.';
        state.uncertain = false;
        res.statusCode = 303; res.setHeader('Location', route); res.end(); return;
      }
      const page = { component: 'inventory/Migration', props: { tenantId: tenant, siteId: site, workspace: state.workspace, notice: state.notice, errors: state.errors }, url: route, version: null, clearHistory: false, encryptHistory: false };
      if (req.headers['x-inertia']) { res.setHeader('X-Inertia', 'true'); return send(page); }
      const value = JSON.stringify(page).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
      const html = await server.transformIndexHtml(route, `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="app" data-page="${value}"></div><script type="module" src="/tests/browser-p08/entry.ts"></script></body></html>`);
      res.setHeader('Content-Type', 'text/html'); res.end(html);
    });
  } }],
  server: { host: '127.0.0.1', port: 4188, strictPort: true },
});
