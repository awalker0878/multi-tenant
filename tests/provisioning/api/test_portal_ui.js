'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const { webcrypto } = require('node:crypto');

const portal = path.resolve(__dirname, '../../..', 'provisioner/controlplane/api/portal/app.js');
const script = fs.readFileSync(portal, 'utf8');
const origin = 'https://mobility.example.org';
const issuer = 'https://identity.example.org/realms/hosting';
const digest = 'a'.repeat(64);

class Element {
  constructor(name = '') {
    this.name = name;
    this.children = [];
    this.listeners = {};
    this.value = '';
    this.checked = false;
    this.disabled = false;
    this.hidden = false;
    this.textContent = '';
  }
  replaceChildren(...children) {
    this.children = children;
    if (['approval-role', 'wsd-selector', 'discovery-environment'].includes(this.name)) {
      this.value = children[0]?.value ?? '';
    }
  }
  append(...children) { this.children.push(...children); }
  add(child) { this.children.push(child); }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  get childElementCount() { return this.children.length; }
}

function samplePlan() {
  const scope = (site, domain, endpoint, native, family) => ({
    organizationId: 'org-01', tenantId: 'tenant-01', siteId: site,
    securityDomainId: domain, endpointId: endpoint,
    nativeScopeId: native, platformFamily: family
  });
  return {
    planId: 'plan-01', planRevision: 7, planDigest: digest,
    workloadId: 'workload-01', workloadRevision: 3,
    frozenAt: '2026-09-27T12:00:00Z',
    sourceSnapshotId: 'snapshot-a', destinationSnapshotId: 'snapshot-b',
    source: scope('site-a', 'wsd-a', 'vcenter-a', 'cluster-01', 'vmware'),
    destination: scope('site-b', 'wsd-b', 'prism-b', 'container-02', 'nutanix'),
    routeMethod: 'COLD_VM_CONVERSION', selectedMachineCount: 2,
    selectedDatasetCount: 3, maxDowntimeSeconds: 3600,
    maxDataLossSeconds: 0, rollbackWindowSeconds: 7200,
    eligibleRoles: ['SOURCE_OWNER']
  };
}

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

async function harness({ stepUpAcr = 'urn:enterprise:mfa', receiptDigest = digest,
  exchange, scopes, environments, discovery, observedObjects } = {}) {
  const elements = new Map();
  const element = (id) => {
    if (!elements.has(id)) elements.set(id, new Element(id));
    return elements.get(id);
  };
  element('approval-ttl').value = '15';
  element('plan-id').value = 'plan-01';
  const popups = [];
  const approvalRequests = [];
  const window = {
    location: { origin },
    listeners: {},
    addEventListener(name, callback) { this.listeners[name] = callback; },
    open() {
      const popup = { closed: false, authUrl: null, close() { this.closed = true; },
        focus() {}, location: { replace(url) { popup.authUrl = url; } } };
      popups.push(popup);
      return popup;
    }
  };
  const json = (value, status = 200) => ({
    ok: status >= 200 && status < 300, status,
    async json() { return value; }
  });
  const fetch = async (url, options = {}) => {
    if (url === '/portal/config.json') return json({
      origin, issuer, authorizeUrl: issuer + '/auth',
      redirectUri: origin + '/portal/callback', clientId: 'portal',
      audience: 'hosting-api', scope: 'openid profile', stepUpAcr
    });
    if (url === '/portal/token') return exchange ? exchange() : json({ access_token: 'opaque', token_type: 'Bearer' });
    if (url === '/v1/access/scopes') return scopes ? scopes() : json({ items: [] });
    if (url.startsWith('/v1/environments?')) return environments ? environments(url) : json({ items: [], nextAfter: null });
    if (url.match(/^\/v1\/environments\/[^/]+\/discovery\/generations\/latest$/)) {
      return discovery ? discovery(url) : json({ error: {} }, 404);
    }
    if (url.match(/^\/v1\/environments\/[^/]+\/discovery\/generations\/[0-9]+\/objects\?/)) {
      return observedObjects ? observedObjects(url) : json({ items: [], nextAfter: null });
    }
    if (url === '/v1/plans/plan-01/review') return json(samplePlan());
    if (url === '/v1/plans/plan-01/approvals') {
      approvalRequests.push(JSON.parse(options.body));
      return json({ approvalId: 'approval-01', planId: 'plan-01',
        planRevision: 7, planDigest: receiptDigest, role: 'SOURCE_OWNER',
        expiresAt: '2026-09-27T12:15:00Z' }, 201);
    }
    throw new Error('Unexpected fetch: ' + url);
  };
  const context = {
    document: { getElementById: element, createElement: (name) => new Element(name) },
    window, fetch, crypto: webcrypto, btoa, TextEncoder, URL, Date,
    Option: function Option(label, value) { return { label, value }; },
    setTimeout: () => 1, clearTimeout: () => {}
  };
  vm.runInNewContext(script, context, { filename: portal });
  await new Promise(setImmediate);
  async function beginAuth(forApproval) {
    await context.signIn(forApproval);
    const popup = popups.at(-1);
    const params = new URL(popup.authUrl).searchParams;
    const finish = () => context.receiveAuthorization({ origin, source: popup, data: {
      kind: 'mobility-oidc-response', state: params.get('state'), issuer,
      code: 'code12345', error: null
    } });
    return { params, finish };
  }
  async function authenticate(forApproval) {
    const { params, finish } = await beginAuth(forApproval);
    await finish();
    return params;
  }
  return { context, element, authenticate, beginAuth, approvalRequests, json };
}

test('approval requires configured step-up and fresh exact plan review', async () => {
  const { context, element, authenticate, approvalRequests } = await harness();
  await authenticate(false);
  await context.loadReview();
  assert.equal(element('review-details').hidden, false);
  assert.equal(element('approval-panel').hidden, false);
  assert.equal(element('approve').disabled, true);
  assert.equal(element('review-source').children.at(-1).children.at(-1).textContent, 'vmware');
  assert.equal(element('review-destination').children.at(-1).children.at(-1).textContent, 'nutanix');
  await context.recordApproval();
  assert.equal(approvalRequests.length, 0);

  const params = await authenticate(true);
  assert.equal(params.get('acr_values'), 'urn:enterprise:mfa');
  assert.equal(params.get('max_age'), '0');
  assert.equal(params.get('prompt'), 'login');
  assert.equal(element('review-details').hidden, true);
  await context.loadReview();
  element('approval-role').value = 'SOURCE_OWNER';
  element('approval-confirm').checked = true;
  context.updateApprovalControls();
  assert.equal(element('approve').disabled, false);
  await context.recordApproval();
  assert.equal(approvalRequests.length, 1);
  assert.equal(approvalRequests[0].expectedPlanRevision, 7);
  assert.equal(approvalRequests[0].expectedPlanDigest, digest);
  assert.equal(approvalRequests[0].role, 'SOURCE_OWNER');
  assert.equal(approvalRequests[0].ttlSeconds, 900);
  assert.match(element('approval-status').textContent, /approval-01 recorded/i);
  assert.equal(element('approve').disabled, true);
});

test('mismatched receipt is not presented as an approval of reviewed plan', async () => {
  const { context, element, authenticate } = await harness({ receiptDigest: 'b'.repeat(64) });
  await authenticate(true);
  await context.loadReview();
  element('approval-role').value = 'SOURCE_OWNER';
  element('approval-confirm').checked = true;
  await context.recordApproval();
  assert.match(element('approval-status').textContent, /differs from the reviewed plan/i);
  assert.equal(element('approve').disabled, true);
});

test('approval controls remain hidden when step-up is not configured', async () => {
  const { context, element, authenticate, approvalRequests } = await harness({ stepUpAcr: null });
  await authenticate(false);
  await context.loadReview();
  assert.equal(element('review-details').hidden, false);
  assert.equal(element('approval-panel').hidden, true);
  await context.recordApproval();
  assert.equal(approvalRequests.length, 0);
});

test('clearing the tab during token exchange cannot restore the old identity', async () => {
  const waiting = deferred();
  const { context, element, beginAuth, json } = await harness({ exchange: () => waiting.promise });
  const { finish } = await beginAuth(false);
  const completion = finish();
  context.clearSession('Signed out.');
  waiting.resolve(json({ access_token: 'old-actor', token_type: 'Bearer' }));
  await completion;
  assert.equal(element('clear-session').disabled, true);
  assert.equal(element('sign-in').disabled, false);
  assert.equal(element('session-status').textContent, 'Signed out.');
  await assert.rejects(context.apiGet('/v1/access/scopes'), /Sign in first/);
});

test('late responses from an old actor never replace or sign out a new actor', async () => {
  for (const oldStatus of [200, 401]) {
    const waiting = deferred();
    let calls = 0;
    const { context, element, beginAuth, authenticate, json } = await harness({
      // A refreshed token can have the same bytes; generation still separates responses.
      exchange: () => { calls++; return json({ access_token: 'same-opaque-token', token_type: 'Bearer' }); },
      scopes: () => calls === 1 ? waiting.promise : json({ items: [{
        kind: 'PORTFOLIO', role: 'WORKLOAD_READER', securityDomainId: 'new-wsd'
      }] })
    });
    const { finish } = await beginAuth(false);
    const oldCompletion = finish();
    await new Promise(setImmediate);
    context.clearSession('Switch identity.');
    await authenticate(false);
    assert.equal(element('wsd-selector').children[1].value, 'new-wsd');
    waiting.resolve(oldStatus === 200 ? json({ items: [{
      kind: 'PORTFOLIO', role: 'WORKLOAD_READER', securityDomainId: 'old-wsd'
    }] }) : json({ error: {} }, 401));
    await oldCompletion;
    assert.equal(element('wsd-selector').children[1].value, 'new-wsd');
    assert.equal(element('clear-session').disabled, false);
    assert.equal(element('sign-in').disabled, true);
  }
});

test('the portal shows exact native-scope declarations as unverified', async () => {
  const { context, element, authenticate, json } = await harness({
    scopes: () => json({ items: [{ kind: 'NATIVE', role: 'JOB_READER',
      securityDomainId: 'wsd-01' }] }),
    environments: (url) => {
      assert.match(url, /wsdId=wsd-01/);
      return json({ items: [{ environmentId: 'environment-01', displayName: 'Candidate',
        siteId: 'site-01', securityDomainId: 'wsd-01', endpointId: 'endpoint-01',
        nativeScopeId: 'cluster-01', platformFamily: 'vmware',
        status: 'DECLARED_UNVERIFIED' }], nextAfter: null });
    }
  });
  await authenticate(false);
  assert.equal(element('environment-selector').children[1].value, 'wsd-01');
  element('environment-wsd').value = 'wsd-01';
  await context.loadEnvironments(true);
  assert.equal(element('environment-rows').children.length, 1);
  assert.equal(element('environment-rows').children[0].children.at(-1).textContent,
    'DECLARED_UNVERIFIED');
  context.clearSession();
  assert.equal(element('environment-rows').children.length, 0);
});

const environment = (id = 'environment-01') => ({
  environmentId: id, displayName: `Candidate ${id}`, siteId: 'site-01',
  securityDomainId: 'wsd-01', endpointId: 'endpoint-01', nativeScopeId: 'cluster-01',
  platformFamily: 'vmware', status: 'DECLARED_UNVERIFIED'
});
const generation = (id = 'environment-01', completeness = 'PARTIAL') => ({
  environmentId: id, generation: 7, campaignId: 'campaign-07', resultDigest: digest,
  capturedAt: '2026-09-27T15:00:00Z', completeness, objectCount: 2,
  collectionErrorCount: 1, missingPrivilegeCount: 1
});

test('authorized environment renders generation gaps and only paged identity summaries', async () => {
  const requests = [];
  const { context, element, authenticate, json } = await harness({
    scopes: () => json({ items: [{ kind: 'NATIVE', role: 'JOB_READER',
      securityDomainId: 'wsd-01' }] }),
    environments: () => json({ items: [environment()], nextAfter: null }),
    discovery: (url) => {
      requests.push(url);
      return json(generation());
    },
    observedObjects: (url) => {
      requests.push(url);
      if (!url.includes('&after=')) return json({ environmentId: 'environment-01',
        generation: 7, items: [{ resourceKind: 'vm', nativeId: 'vm-101',
          displayName: 'Database', unknownCount: 2, objectDigest: digest,
          facts: [{ name: 'secret_raw_fact', value: 'must-never-render' }] }],
        nextAfter: 'opaque-page' });
      return json({ environmentId: 'environment-01', generation: 7,
        items: [{ resourceKind: 'vm', nativeId: 'vm-102', displayName: null,
          unknownCount: 0, objectDigest: digest }], nextAfter: null });
    }
  });
  await authenticate(false);
  element('environment-wsd').value = 'wsd-01';
  await context.loadEnvironments(true);
  element('discovery-environment').value = 'environment-01';
  await context.loadDiscovery();
  assert.equal(element('discovery-details').hidden, false);
  assert.match(element('discovery-completeness').textContent, /Partial/);
  assert.equal(element('discovery-errors').textContent, '1');
  assert.equal(element('discovery-rows').children.length, 1);
  assert.equal(element('discovery-rows').children[0].children[1].textContent, 'vm-101');
  assert.equal(element('discovery-rows').children[0].children[2].textContent, 'Database');
  assert.equal(element('more-discovery').hidden, false);
  await context.loadObservedObjects();
  assert.equal(element('discovery-rows').children.length, 2);
  assert.equal(element('more-discovery').hidden, true);
  assert.equal(requests.length, 3);
  assert.ok(requests[2].includes('/generations/7/objects?limit=50&after=opaque-page'));
  assert.ok(!JSON.stringify(element('discovery-rows').children).includes('secret_raw_fact'));
});

test('reported complete still says visibility is unverified; token change clears observations', async () => {
  const { context, element, authenticate, json } = await harness({
    scopes: () => json({ items: [{ kind: 'NATIVE', role: 'JOB_READER',
      securityDomainId: 'wsd-01' }] }),
    environments: () => json({ items: [environment()], nextAfter: null }),
    discovery: () => json({ ...generation('environment-01', 'COMPLETE'),
      collectionErrorCount: 0, missingPrivilegeCount: 0 }),
    observedObjects: () => json({ environmentId: 'environment-01', generation: 7,
      items: [], nextAfter: null })
  });
  await authenticate(false);
  element('environment-wsd').value = 'wsd-01';
  await context.loadEnvironments(true);
  element('discovery-environment').value = 'environment-01';
  await context.loadDiscovery();
  assert.match(element('discovery-completeness').textContent, /native visibility unverified/i);
  assert.equal(element('discovery-details').hidden, false);
  context.clearSession();
  assert.equal(element('discovery-rows').children.length, 0);
  assert.equal(element('discovery-details').hidden, true);
  assert.equal(element('discovery-environment').disabled, true);
});

test('no available generation leaves identity table empty', async () => {
  const { context, element, authenticate, json } = await harness({
    scopes: () => json({ items: [{ kind: 'NATIVE', role: 'JOB_READER',
      securityDomainId: 'wsd-01' }] }),
    environments: () => json({ items: [environment()], nextAfter: null }),
    discovery: () => json({ error: {} }, 404)
  });
  await authenticate(false);
  element('environment-wsd').value = 'wsd-01';
  await context.loadEnvironments(true);
  element('discovery-environment').value = 'environment-01';
  await context.loadDiscovery();
  assert.match(element('discovery-status').textContent, /No observation is available/);
  assert.equal(element('discovery-details').hidden, true);
  assert.equal(element('discovery-rows').children.length, 0);
});

test('contradictory complete summary is rejected before identity rendering', async () => {
  const { context, element, authenticate, json } = await harness({
    scopes: () => json({ items: [{ kind: 'NATIVE', role: 'JOB_READER',
      securityDomainId: 'wsd-01' }] }),
    environments: () => json({ items: [environment()], nextAfter: null }),
    discovery: () => json(generation('environment-01', 'COMPLETE'))
  });
  await authenticate(false);
  element('environment-wsd').value = 'wsd-01';
  await context.loadEnvironments(true);
  element('discovery-environment').value = 'environment-01';
  await context.loadDiscovery();
  assert.match(element('discovery-status').textContent, /does not match/);
  assert.equal(element('discovery-details').hidden, true);
});

test('old actor or changed environment cannot install late discovery response', async () => {
  const waiting = deferred();
  const { context, element, authenticate, json } = await harness({
    scopes: () => json({ items: [{ kind: 'NATIVE', role: 'JOB_READER',
      securityDomainId: 'wsd-01' }] }),
    environments: () => json({ items: [environment('environment-01'),
      environment('environment-02')], nextAfter: null }),
    discovery: (url) => url.includes('environment-01') ? waiting.promise :
      json(generation('environment-02', 'UNKNOWN')),
    observedObjects: () => json({ environmentId: 'environment-02', generation: 7,
      items: [], nextAfter: null })
  });
  await authenticate(false);
  element('environment-wsd').value = 'wsd-01';
  await context.loadEnvironments(true);
  element('discovery-environment').value = 'environment-01';
  const old = context.loadDiscovery();
  element('discovery-environment').value = 'environment-02';
  context.clearDiscovery();
  await context.loadDiscovery();
  waiting.resolve(json(generation('environment-01')));
  await old;
  assert.equal(element('discovery-generation').textContent, '7');
  assert.match(element('discovery-completeness').textContent, /Unknown/);
  context.clearSession();
  assert.equal(element('discovery-details').hidden, true);
});

test('late object page cannot repopulate rows after token clearance', async () => {
  const waiting = deferred();
  const { context, element, authenticate, json } = await harness({
    scopes: () => json({ items: [{ kind: 'NATIVE', role: 'JOB_READER',
      securityDomainId: 'wsd-01' }] }),
    environments: () => json({ items: [environment()], nextAfter: null }),
    discovery: () => json(generation()),
    observedObjects: () => waiting.promise
  });
  await authenticate(false);
  element('environment-wsd').value = 'wsd-01';
  await context.loadEnvironments(true);
  element('discovery-environment').value = 'environment-01';
  const loading = context.loadDiscovery();
  await new Promise(setImmediate);
  context.clearSession('Signed out.');
  waiting.resolve(json({ environmentId: 'environment-01', generation: 7,
    items: [{ resourceKind: 'vm', nativeId: 'vm-101', displayName: 'Old actor VM',
      unknownCount: 0, objectDigest: digest }], nextAfter: null }));
  await loading;
  assert.equal(element('discovery-rows').children.length, 0);
  assert.equal(element('discovery-details').hidden, true);
});
