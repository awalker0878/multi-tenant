import { randomUUID } from 'node:crypto';
import type { Plugin } from 'vite';

export function fleetFixture(): Plugin {
  const tenant = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
  const site = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
  const base = `/tenants/${tenant}/inventory/sites/${site}/migration-fleet`;
  let state: any;
  function reset() {
    const now = Math.floor(Date.now() / 1000);
    const target = { id: randomUUID(), native_id: 'OpenStack · project-finance', current: true, expires_at: now + 600, holds: [], disk_formats: ['raw', 'qcow2'] };
    const items = ['accounts-api', 'accounts-db', 'legacy <img src=x onerror=alert(1)>'].map((name, i) => ({ resource_id: randomUUID(), endpoint_id: site, endpoint_label: 'vCenter Ottawa', native_scope: 'datacenter-1', native_id: `vm-${i + 1}`, name, generation_id: randomUUID(), profile_id: i === 2 ? null : randomUUID(), source_identity_sha256: i === 2 ? null : 'a'.repeat(64), power_state: i === 0 ? 'poweredOff' : 'poweredOn', cpu: i === 1 ? 8 : 2, memory_mb: i === 1 ? 16384 : 4096, guest_id: i === 2 ? null : 'ubuntu64Guest', disk_count: i === 2 ? null : 2, disk_bytes: i === 2 ? null : 85899345920, collected_at: now, expires_at: now + 600, holds: i === 2 ? ['source_profile_required'] : [], readiness: i === 2 ? 'held' : 'review_required' }));
    state = { posts: [], preparations: [], plan_requests: [], plan_uncertain: false, plan_id: randomUUID(),
      plan_options: ['rehearsal', 'cutover'].map(mode => ({recipe_id: randomUUID(), base_plan_id: randomUUID(), mode, method: 'VM_COLD_EXPORT', expires_at: now + 600, stages: 8})),
      errors: {}, notice: null, access: 200, uncertain: false, group: null, detail: null,
      workspace: { items, next_cursor: site, targets: [target], groups: [], native_write_authorized: false },
      extra: { ...items[0], resource_id: randomUUID(), native_id: 'vm-4', name: 'batch-worker', profile_id: randomUUID() },
      endpoints: { items: [{ endpoint_id: site, label: 'vCenter Ottawa', native_scope: 'datacenter-1', platform: 'vmware' }], next_cursor: null } };
  }
  reset();
  return { name: 'p08-fleet-fixture', configureServer(server) {
    server.middlewares.use(async (req, res, next) => {
      const path = req.url?.split('?')[0] ?? '';
      if (!path.startsWith(base) && path !== '/__fleet') return next();
      let body = ''; for await (const chunk of req) body += chunk;
      const send = (value: unknown, status = 200) => { res.statusCode = status; res.setHeader('Content-Type', 'application/json'); res.setHeader('Cache-Control', 'no-store'); res.end(JSON.stringify(value)); };
      if (path === '/__fleet') { if (req.method === 'POST') { const c = JSON.parse(body); if (c.reset) reset(); if (c.access) state.access = c.access; if (c.uncertain) state.uncertain = true; if (c.plan_uncertain) state.plan_uncertain = true; if (c.stale) state.stale = true; } return send(state); }
      if (path.endsWith('/status')) return send({ available: true }, state.access);
      if (path.endsWith('/page')) return send({ ...state.workspace, items: [state.extra], next_cursor: null });
      if (path.endsWith('/prepare')) {
        const command = JSON.parse(body); (command.operation ? state.plan_requests : state.preparations).push(command);
        if (state.stale) return send({ error: 'stale_group' }, 412);
        const vm = state.detail.members.find((m: any) => m.candidate.resource_id === command.resource_id);
        if (vm.holds.length) return send({ error: 'migration_member_held', holds: vm.holds }, 409);
        if (command.operation === 'options') return send({ items: state.plan_options, native_write_authorized: false });
        if (command.operation === 'compose') {
          if (state.plan_uncertain) { state.plan_uncertain = false; return send({error: 'planning_unavailable'}, 503); }
          return send({ id: state.plan_id, kind: 'plan', binding: { digest: 'a'.repeat(64) }, native_write_authorized: false });
        }
        return send({ binding: { method: 'VM_COLD_EXPORT', review: { revision: 1, digest: 'a'.repeat(64) } }, native_write_authorized: false });
      }
      if (req.method === 'POST') {
        const command = JSON.parse(body); state.posts.push(command);
        if (path.endsWith('/refresh')) { state.notice = 'API discovery queued.'; res.statusCode = 303; res.setHeader('Location', base); res.end(); return; }
        const input = command.selection;
        state.group = { id: state.group?.id ?? randomUUID(), revision: state.group ? state.group.revision + 1 : 1, digest: 'b'.repeat(64), input: { ...input, resource_ids: undefined, members: input.resource_ids.map((id: string) => ({ resource_id: id, source_identity_sha256: 'a'.repeat(64) })) } };
        state.workspace.groups = [state.group];
        state.detail = { group: state.group, native_write_authorized: false, members: input.resource_ids.map((id: string, i: number) => ({ candidate: [...state.workspace.items, state.extra].find((v: any) => v.resource_id === id), holds: i === 1 ? ['confirmed_vm_review_required'] : [], preparation: i === 1 ? null : { site_id: site, review: { revision: 1, digest: 'a'.repeat(64) }, disks: [] } })) };
        state.errors = state.uncertain ? { inventory_status: '503', command: 'The result is uncertain. Retry this exact command unchanged.' } : {};
        state.uncertain = false;
        res.statusCode = 303; res.setHeader('Location', `${base}/groups/${state.group.id}`); res.end(); return;
      }
      const page = { component: 'inventory/Fleet', props: { tenantId: tenant, siteId: site, workspace: state.workspace, detail: path.includes('/groups/') ? state.detail : null, endpoints: state.endpoints, notice: state.notice, errors: state.errors }, url: path, version: null, clearHistory: false, encryptHistory: false };
      if (req.headers['x-inertia']) { res.setHeader('X-Inertia', 'true'); return send(page); }
      const data = JSON.stringify(page).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
      const html = await server.transformIndexHtml(base, `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app" data-page="${data}"></div><script type="module" src="/tests/browser-p08/entry.ts"></script></body></html>`);
      res.setHeader('Content-Type', 'text/html'); res.end(html);
    });
  } };
}
