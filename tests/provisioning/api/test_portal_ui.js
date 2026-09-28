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
    if (['approval-role', 'wsd-selector', 'discovery-environment', 'comparison-workload',
      'destination-wsd', 'destination-environment'].includes(this.name)) {
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
  exchange, scopes, environments, discovery, observedObjects, comparison } = {}) {
  const elements = new Map();
  const element = (id) => {
    if (!elements.has(id)) elements.set(id, new Element(id));
    return elements.get(id);
  };
  element('approval-ttl').value = '15';
  element('plan-id').value = 'plan-01';
  const popups = [];
  const approvalRequests = [];
  const comparisonRequests = [];
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
    if (url === '/v1/assessments/compare') {
      const body = JSON.parse(options.body);
      comparisonRequests.push(body);
      return comparison ? comparison(body) : json(comparisonResponse(body));
    }
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
  return { context, element, authenticate, beginAuth, approvalRequests, comparisonRequests, json };
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

function comparisonResponse(body) {
  const input = (selection) => ({ ...selection,
    endpointId: 'endpoint-' + selection.environmentId,
    nativeScopeId: 'scope-' + selection.environmentId, platformFamily: 'vmware',
    productTupleId: 'reviewed-tuple', productTupleDigest: digest, observation: null,
    superseded: false, latestObservation: { generation: selection.generation,
      rawSnapshotDigest: digest, capturedAt: '2026-09-28T11:00:00Z',
      collectionCompleteness: 'COMPLETE', collectionErrors: [], missingPrivileges: [] } });
  const sourceInput = input(body.source);
  const destinationInputs = body.destinations.map(input);
  return { format: 'hosting-discovery-comparison/1', executionAuthorized: false,
    assessedAt: '2026-09-28T12:00:00Z', sourceInput, destinationInputs,
    assessments: destinationInputs.map((destination, index) => ({
      format: 'hosting-destination-assessment/1', executionAuthorized: false,
      source: sourceInput, destination,
      workload: { endpointId: sourceInput.endpointId, nativeScopeId: sourceInput.nativeScopeId,
        platformFamily: sourceInput.platformFamily, nativeId: body.workloadNativeId, resourceKind: 'vm' },
      method: body.method, guestProfile: body.guestProfile, networkMode: body.networkMode,
      dataMode: body.dataMode, routeMaturity: 'NOT_QUALIFIED',
      status: index === 0 ? 'UNKNOWN' : 'BLOCKED',
      issues: [{ severity: index === 0 ? 'UNKNOWN' : 'BLOCKER', code: 'MISSING_EVIDENCE',
        reason: '<img src=x onerror=alert(1)> Missing observed capacity',
        remediation: 'Collect current capacity facts and verify the destination.' }],
      estimate: { transferBytes: null, copyPhaseSeconds: null, confidence: 'NONE',
        basis: ['Current throughput is unknown.'] }
    })) };
}

async function comparisonHarness(options = {}) {
  let json;
  const target = await harness({
    scopes: () => json({ items: [{ kind: 'NATIVE', role: 'JOB_READER', securityDomainId: 'wsd-01' },
      { kind: 'NATIVE', role: 'JOB_READER', securityDomainId: 'wsd-02' }] }),
    environments: (url) => json({ items: url.includes('wsdId=wsd-02')
      ? [environment('environment-02'), environment('environment-03')].map((item) => ({
        ...item, securityDomainId: 'wsd-02', displayName: item.environmentId === 'environment-02'
          ? '<script>destination</script>' : 'Recovery environment' }))
      : [environment()], nextAfter: null }),
    discovery: (url) => {
      if (options.discovery) return options.discovery(url, json);
      const id = url.split('/')[3];
      return json({ ...generation(id), generation: id === 'environment-03' ? 9 : 7 });
    },
    observedObjects: () => json({ environmentId: 'environment-01', generation: 7,
      items: [{ resourceKind: 'vm', nativeId: 'folder/vm:101', displayName: 'Existing VM',
        unknownCount: 2, objectDigest: digest },
      { resourceKind: 'network', nativeId: 'network-01', displayName: 'Network',
        unknownCount: 0, objectDigest: digest }], nextAfter: null }),
    comparison: options.comparison
  });
  json = target.json;
  const { context, element, authenticate } = target;
  await authenticate(false);
  element('environment-wsd').value = 'wsd-01';
  await context.loadEnvironments(true);
  element('discovery-environment').value = 'environment-01';
  await context.loadDiscovery();
  element('comparison-workload').value = 'folder/vm:101';
  element('comparison-method').value = 'COLD_VM_CONVERSION';
  element('comparison-guest').value = 'linux-uefi';
  element('comparison-network').value = 'renumber';
  element('comparison-data').value = 'image-copy';
  element('destination-wsd').value = 'wsd-02';
  await context.loadDestinationEnvironments(true);
  if (!options.deferDestinations) {
    for (const id of ['environment-02', 'environment-03']) {
      element('destination-environment').value = id;
      await context.addDestination();
    }
  }
  return target;
}

function descendantText(element) {
  return [element.textContent || '', ...(element.children || []).map(descendantText)].join(' ');
}

test('comparison selects observed VM, pins two destination generations, and renders unknowns safely', async () => {
  const { context, element, comparisonRequests } = await comparisonHarness();
  assert.equal(element('comparison-workload').children.length, 2);
  assert.equal(element('destination-rows').children.length, 2);
  assert.equal(element('compare-destinations').disabled, false);
  await context.compareDestinations();
  assert.deepEqual(comparisonRequests[0], {
    source: { environmentId: 'environment-01', generation: 7 }, workloadNativeId: 'folder/vm:101',
    destinations: [{ environmentId: 'environment-02', generation: 7 },
      { environmentId: 'environment-03', generation: 9 }], method: 'COLD_VM_CONVERSION',
    guestProfile: 'linux-uefi', networkMode: 'renumber', dataMode: 'image-copy'
  });
  const cards = element('comparison-results');
  assert.equal(cards.hidden, false);
  assert.equal(cards.children.length, 2);
  assert.equal(cards.children[0].children[0].textContent, '<script>destination</script> · environment-02');
  assert.match(descendantText(cards), /UNKNOWN · assessment only/);
  assert.match(descendantText(cards), /BLOCKED · assessment only/);
  assert.match(descendantText(cards), /<img src=x onerror=alert\(1\)>/);
  assert.match(descendantText(cards), /Next: Collect current capacity/);
  assert.match(descendantText(cards), /Copy phase estimate: Unknown/);
  assert.match(element('comparison-status').textContent, /Execution is not authorized/);
  assert.ok(!script.includes('innerHTML'));
});

test('capacity selectors map exact identity and any edit clears old comparison', async () => {
  const { context, element, comparisonRequests } = await comparisonHarness();
  const fields = element('destination-rows').children[0].children[2].children[0].children;
  const kind = fields[0].children[0];
  const native = fields[1].children[0];
  kind.value = 'cluster';
  kind.listeners.change();
  await context.compareDestinations();
  assert.equal(comparisonRequests.length, 0);
  assert.match(element('comparison-status').textContent, /require both/);
  native.value = 'cluster/path:02';
  native.listeners.input();
  await context.compareDestinations();
  assert.equal(comparisonRequests[0].destinations[0].capacityKind, 'cluster');
  assert.equal(comparisonRequests[0].destinations[0].capacityNativeId, 'cluster/path:02');
  assert.equal(element('comparison-results').hidden, false);
  native.value = 'cluster/path:03';
  native.listeners.input();
  assert.equal(element('comparison-results').hidden, true);
  assert.equal(element('comparison-results').children.length, 0);
});

test('fabricated VM selection and fewer than two destinations never invoke assessment', async () => {
  const { context, element, comparisonRequests } = await comparisonHarness();
  element('comparison-workload').value = 'never-observed';
  await context.compareDestinations();
  assert.equal(comparisonRequests.length, 0);
  element('comparison-workload').value = 'folder/vm:101';
  element('destination-rows').children[0].children[3].children[0].listeners.click();
  await context.compareDestinations();
  assert.equal(comparisonRequests.length, 0);
  assert.equal(element('compare-destinations').disabled, true);
});

test('late comparison cannot restore results after logout, source or route selection change', async () => {
  for (const change of ['logout', 'source', 'route', 'workload', 'destination']) {
    const waiting = deferred();
    const { context, element, comparisonRequests, json } = await comparisonHarness({ comparison: () => waiting.promise });
    const reading = context.compareDestinations();
    await new Promise(setImmediate);
    if (change === 'logout') context.clearSession();
    if (change === 'source') context.clearDiscovery();
    if (change === 'route') {
      element('comparison-guest').value = 'windows-uefi';
      element('comparison-guest').listeners.input();
    }
    if (change === 'workload') element('comparison-workload').listeners.change();
    if (change === 'destination') element('destination-environment').listeners.change();
    waiting.resolve(json(comparisonResponse(comparisonRequests[0])));
    await reading;
    assert.equal(element('comparison-results').hidden, true, change);
    assert.equal(element('comparison-results').children.length, 0, change);
    if (change === 'logout') {
      assert.equal(element('destination-rows').children.length, 0);
      assert.equal(element('comparison-workload').disabled, true);
      assert.equal(element('destination-wsd').disabled, true);
    }
  }
});

test('mismatched generations, wrong workload and approval claims refuse the entire comparison', async () => {
  for (const mutate of [
    (response) => { response.destinationInputs[1].generation++; },
    (response) => { response.assessments[0].workload.nativeId = 'another-vm'; },
    (response) => { response.assessments[0].executionAuthorized = true; },
    (response) => { response.executionAuthorized = true; },
    (response) => { response.assessments[0].status = 'SUCCEEDED'; },
    (response) => { delete response.sourceInput.latestObservation; },
    (response) => { response.sourceInput.latestObservation.generation++; },
    (response) => { response.destinationInputs[0].superseded = true; },
    (response) => {
      response.sourceInput.latestObservation.generation++;
      response.sourceInput.superseded = true;
      response.assessments[0].status = 'ELIGIBLE';
    }
  ]) {
    let json;
    const target = await comparisonHarness({ comparison: (body) => {
      const response = comparisonResponse(body);
      mutate(response);
      return json(response);
    } });
    json = target.json;
    await target.context.compareDestinations();
    assert.equal(target.element('comparison-results').hidden, true);
    assert.equal(target.element('comparison-results').children.length, 0);
    assert.match(target.element('comparison-status').textContent, /does not match|differs/);
  }
});

test('superseded pins show historical generation and latest collection uncertainty', async () => {
  let json;
  const target = await comparisonHarness({ comparison: (body) => {
    const response = comparisonResponse(body);
    response.sourceInput.superseded = true;
    response.sourceInput.latestObservation.generation++;
    response.sourceInput.latestObservation.collectionCompleteness = 'PARTIAL';
    response.sourceInput.latestObservation.missingPrivileges = ['inventory.read'];
    for (const assessment of response.assessments) {
      assessment.status = 'UNKNOWN';
      assessment.issues.push({ severity: 'UNKNOWN', code: 'SOURCE_SNAPSHOT_SUPERSEDED',
        reason: 'A newer partial observation exists.',
        remediation: 'Load the latest generation and resolve missing privileges.' });
    }
    return json(response);
  } });
  json = target.json;
  await target.context.compareDestinations();
  assert.equal(target.element('comparison-results').hidden, false);
  const text = descendantText(target.element('comparison-results'));
  assert.match(text, /Source: pinned generation 7; latest observed generation 8 \(PARTIAL\)/);
  assert.match(text, /Historical pin; current eligibility unknown/);
  assert.match(text, /SOURCE_SNAPSHOT_SUPERSEDED/);
  assert.match(text, /Load the latest generation and resolve missing privileges/);
});

test('late destination generation cannot repopulate selections after source change', async () => {
  const waiting = deferred();
  let requested = false;
  const target = await comparisonHarness({ deferDestinations: true,
    discovery: (url, json) => {
      if (url.includes('environment-02')) {
        requested = true;
        return waiting.promise;
      }
      return json(generation());
    } });
  assert.equal(target.element('comparison-workload').disabled, false);
  target.element('destination-environment').value = 'environment-02';
  const adding = target.context.addDestination();
  assert.equal(requested, true);
  target.context.clearDiscovery();
  waiting.resolve(target.json(generation('environment-02')));
  await adding;
  assert.equal(target.element('destination-rows').children.length, 0);
});

test('unavailable verified provider leaves no old comparison visible', async () => {
  let response;
  let json;
  const target = await comparisonHarness({ comparison: (body) =>
    response || json(comparisonResponse(body)) });
  json = target.json;
  await target.context.compareDestinations();
  assert.equal(target.element('comparison-results').hidden, false);
  response = json({ error: { code: 'ASSESSMENT_UNAVAILABLE' } }, 503);
  await target.context.compareDestinations();
  assert.equal(target.element('comparison-results').hidden, true);
  assert.match(target.element('comparison-status').textContent, /Verified assessment inputs are unavailable/);
});

test('conditional and eligible assessment results never become execution approval', async () => {
  let json;
  const target = await comparisonHarness({ comparison: (body) => {
    const response = comparisonResponse(body);
    response.assessments[0].status = 'CONDITIONAL';
    response.assessments[0].issues[0].severity = 'CONDITION';
    response.assessments[1].status = 'ELIGIBLE';
    response.assessments[1].issues = [];
    return json(response);
  } });
  json = target.json;
  await target.context.compareDestinations();
  const text = descendantText(target.element('comparison-results'));
  assert.match(text, /CONDITIONAL · assessment only/);
  assert.match(text, /ELIGIBLE · assessment only/);
  assert.match(target.element('comparison-status').textContent, /Execution is not authorized/);
  assert.equal(target.approvalRequests.length, 0);
});
