import type { Plugin } from 'vite';
const tenant = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', site = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const application = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc', environment = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd';
export const nativeRoute = `/tenants/${tenant}/sites/${site}/applications/${application}/environments/${environment}/native-jobs/eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee`;
export function nativeFixture(): Plugin {
  let state: any;
  function reset() { state = { access: 200, posts: [], uncertain: false, view: {
    tenant_id: tenant, job_id: 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee', state: 'held', revision: 3, stopped: false,
    hold_reason: 'native_outcome_unknown', transfer_continuation_candidate: true, control_allowed: true,
    plan_sha256: 'a'.repeat(64), scope: { tenant_id: tenant, site_id: site, environment, resource_id: application, project_id: application },
    operations: [{ stage: 'capture', operation_id: site, redeemed: true, observation_digest: 'b'.repeat(64) },
      { stage: 'export_copy', operation_id: application, redeemed: true, observation_digest: null }],
    measurements: { observed_at: 1791459000, started_at: 1791458800, total_stages: 8, completed_stages: 1,
      transfer: { operation_id: application, measured_at: 1791459000, bytes_completed: 1073741824, disks_completed: 1, artifact_complete: false, evidence_source: 'worker_custody_journal' },
      operations: [{ stage: 'capture', operation_id: site, prepared_at: 1791458800, started_at: 1791458810, observed_at: 1791458870, elapsed_seconds: 60 },
        { stage: 'export_copy', operation_id: application, prepared_at: 1791458870, started_at: 1791458880, observed_at: null, elapsed_seconds: 120 }] },
    retry_authorized: false, native_qualification: 'not_established',
  } }; }
  reset();
  return { name: 'isolated-native-job-observations', configureServer(server) {
    server.middlewares.use(async (req, res, next) => {
      const path = req.url?.split('?')[0];
      if (path !== '/__native' && !path?.startsWith(nativeRoute)) return next();
      let raw = ''; for await (const chunk of req) raw += chunk;
      const send = (v: unknown, code = 200) => { res.statusCode = code; res.setHeader('Content-Type', 'application/json'); res.setHeader('Cache-Control', 'no-store'); res.end(JSON.stringify(v)); };
      if (path === '/__native') {
        if (req.method === 'POST') { const c = JSON.parse(raw); if (c.reset) reset(); if (c.access) state.access = c.access; if (c.uncertain) state.uncertain = true; if (c.revision) state.view.revision = c.revision; if (typeof c.control_allowed === 'boolean') state.view.control_allowed = c.control_allowed; }
        return send(state);
      }
      if (state.access !== 200) return send({ error: 'denied' }, state.access);
      if (path?.endsWith('/status')) return send(state.view);
      if (path?.endsWith('/commands')) {
        const command = JSON.parse(raw); state.posts.push(command);
        if (command.expected_revision !== state.view.revision) return send({ error: 'native_job_revision_changed' }, 409);
        state.view.revision++;
        state.view.transfer_continuation_candidate = false;
        state.view.state = command.action === 'stop' ? 'stopped' : 'running';
        state.view.stopped = command.action === 'stop';
        state.view.hold_reason = command.action === 'stop' ? 'native_stop_requested' : null;
        if (command.action === 'continue-transfer') {
          state.view.operations[1].observation_digest = 'c'.repeat(64);
          state.view.measurements.completed_stages = 2;
          state.view.measurements.operations[1].observed_at = 1791459000;
        }
        return state.uncertain ? send({ error: 'outcome_uncertain' }, 503) : send(state.view, 202);
      }
      const page = { component: 'jobs/NativeJob', props: { tenantId: tenant, base: nativeRoute, initial: state.view }, url: nativeRoute, version: null, clearHistory: false, encryptHistory: false };
      if (req.headers['x-inertia']) { res.setHeader('X-Inertia', 'true'); return send(page); }
      const value = JSON.stringify(page).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
      const html = await server.transformIndexHtml(nativeRoute, `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="app" data-page="${value}"></div><script type="module" src="/tests/browser-p08/entry.ts"></script></body></html>`);
      res.setHeader('Content-Type', 'text/html'); res.end(html);
    });
  } };
}
