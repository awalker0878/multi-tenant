import { randomUUID } from 'node:crypto';
import type { Plugin } from 'vite';

export function campaignFixture(): Plugin {
  const tenant = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', scope = { site_id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', environment: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc', resource_id: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd' };
  const base = `/tenants/${tenant}/sites/${scope.site_id}/applications/${scope.resource_id}/environments/${scope.environment}/migration-campaigns`;
  let state: any;
  const reset = () => { state = { base, posts: [], campaign: null, access: 200, uncertain: false, plan: { plan_id: randomUUID(), plan_revision: 1, plan_digest: 'a'.repeat(64), method: 'VM_COLD_EXPORT', mode: 'rehearsal' } }; };
  reset();
  return { name: 'p08-campaign-fixture', configureServer(server) {
    server.middlewares.use(async (req, res, next) => {
      const path = req.url?.split('?')[0] ?? '';
      if (!path.startsWith(base) && path !== '/__campaign') return next();
      let raw = ''; for await (const chunk of req) { raw += chunk; if (raw.length > 262144) { res.statusCode = 413; res.end(); return; } }
      const send = (body: unknown, code = 200) => { res.statusCode = code; res.setHeader('Content-Type', 'application/json'); res.setHeader('Cache-Control', 'no-store'); res.end(JSON.stringify(body)); };
      if (path === '/__campaign') { if (req.method === 'POST') { const input = JSON.parse(raw); if (input.reset) reset(); if (input.access) state.access = input.access; if (input.uncertain) state.uncertain = true; } return send(state); }
      if (state.access !== 200) return send({ error: 'access_changed' }, state.access);
      const list = () => ({ tenant_id: tenant, scope, items: state.campaign ? [{ ...state.campaign, name: state.campaign.settings.name }] : [], limit_reached: false, control_allowed: true });
      if (path.includes('/plans/')) return send(state.plan);
      if (req.method === 'POST') {
        const body = JSON.parse(raw); state.posts.push({ path, body });
        if (path === base && !state.campaign) {
          state.campaign = { id: randomUUID(), tenant_id: tenant, scope, settings: body.settings, revision: 1, state: 'draft', control_allowed: true, native_write_authorized: false,
            members: body.members.map((m: any) => ({ id: m.id, state: 'queued', reason: 'campaign_measurement_required', job_id: null, specification: { ...m, method: state.plan.method, mode: state.plan.mode }, estimate: { phases: {}, total_seconds: null, outage_seconds: null, holds: ['measurement_required_transfer_concurrency_1'], margin_percent: 25, phase_limits: body.settings.phase_limits } })) };
        } else if (path.endsWith('/commands')) { state.campaign.revision++; state.campaign.state = { schedule: 'scheduled', pause: 'paused', cancel: 'cancelled' }[body.action as 'schedule' | 'pause' | 'cancel']; }
        if (state.uncertain) { state.uncertain = false; return send({ error: 'response_lost' }, 503); }
        return send({ id: state.campaign.id, state: state.campaign.state }, 202);
      }
      const campaignId = path.slice(base.length).split('/')[1];
      const initial = campaignId && campaignId !== 'status' ? state.campaign : list();
      if (path.endsWith('/status')) return send(initial);
      const page = { component: 'jobs/Campaigns', props: { tenantId: tenant, base, initial, campaignId: campaignId || null }, url: path, version: null, clearHistory: false, encryptHistory: false };
      if (req.headers['x-inertia']) { res.setHeader('X-Inertia', 'true'); return send(page); }
      const data = JSON.stringify(page).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
      const html = await server.transformIndexHtml(base, `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app" data-page="${data}"></div><script type="module" src="/tests/browser-p08/entry.ts"></script></body></html>`);
      res.setHeader('Content-Type', 'text/html'); res.end(html);
    });
  } };
}
