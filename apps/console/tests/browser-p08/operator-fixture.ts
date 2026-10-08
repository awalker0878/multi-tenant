// Isolated HTTP presentation checks; persistence/authorization are tested in their owners.
import { readFileSync } from 'node:fs';
import type { Plugin } from 'vite';
const fixture = JSON.parse(readFileSync('../../contracts/fixtures/inventory/operator-readiness-v1.json', 'utf8'));
const route = `/tenants/${fixture.tenant_id}/inventory/sites/${fixture.site_id}/operator-inputs`;
let state: any;
function reset() { state = { workspace: structuredClone(fixture), errors: {}, notice: null, posts: [], uncertain: false, stale: false, access: 200 }; }
reset();
export function operatorFixture(): Plugin { return { name: 'operator-inputs-fixture', configureServer(server) {
  server.middlewares.use(async (req, res, next) => {
    const path = req.url?.split('?')[0];
    if (!path || (!path.startsWith(route) && path !== '/__operators')) return next();
    let body = ''; for await (const chunk of req) body += chunk;
    const send = (value: unknown, status = 200) => { res.statusCode = status; res.setHeader('Content-Type', 'application/json'); res.setHeader('Cache-Control', 'no-store'); res.end(JSON.stringify(value)); };
    if (path === '/__operators') {
      if (req.method === 'POST') { const control = JSON.parse(body); if (control.reset) reset(); if (control.record) state.workspace.record = control.record; for (const key of ['uncertain', 'stale', 'access']) if (key in control) state[key] = control[key]; }
      if (req.method === 'POST') { const control = JSON.parse(body); if (control.evidence) { state.workspace.checks = state.workspace.checks.map((check: any) => check.field_id === control.evidence.field_id ? { ...check, ...control.evidence } : check); } } return send(state);
    }
    if (path.endsWith('/status')) return send({ available: true }, state.access);
    if (path.endsWith('/download')) { res.setHeader('Content-Disposition', 'attachment; filename="operator-inputs.json"'); return send({ qualification_status: 'not_established', ...state.workspace }); }
    if (req.method === 'POST') {
      const command = JSON.parse(body); state.posts.push(command);
      state.errors = state.stale ? { inventory_status: '412', command: 'A saved revision or environment review changed.' } : state.uncertain ? { inventory_status: '503', command: 'The result is uncertain. Recover the unchanged save before editing further.' } : {};
      if (!state.stale) { state.workspace.record = { revision: 1, digest: 'a'.repeat(64), values: command.input.values, configuration_digest: command.input.configuration_digest, saved_at: Date.now()/1000 }; state.workspace.context = command.input.context; const required = state.workspace.contexts.find((context: any) => context.operation === command.input.context.operation && context.method === command.input.context.method).required_fields;
        state.workspace.missing_fields = required.filter((id: string) => !(id in command.input.values));
        state.workspace.checks = state.workspace.checks.map((check: any) => ({ ...check, state: !required.includes(check.field_id) ? 'not_applicable' : check.field_id in command.input.values ? 'unverified' : 'missing' })); }
      state.notice = Object.keys(state.errors).length ? null : 'Operator inputs saved. Remaining requirements are listed below.';
      state.uncertain = false; state.stale = false;
      res.statusCode = 303; res.setHeader('Location', route); res.end(); return;
    }
    const page = { component: 'inventory/OperatorInputs', props: { tenantId: fixture.tenant_id, siteId: fixture.site_id, workspace: state.workspace, errors: state.errors, notice: state.notice }, url: route, version: null, clearHistory: false, encryptHistory: false };
    if (req.headers['x-inertia']) { res.setHeader('X-Inertia', 'true'); return send(page); }
    const value = JSON.stringify(page).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
    res.setHeader('Content-Type', 'text/html');
    res.end(await server.transformIndexHtml(route, `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="app" data-page="${value}"></div><script type="module" src="/tests/browser-p08/entry.ts"></script></body></html>`));
  });
} }; }
