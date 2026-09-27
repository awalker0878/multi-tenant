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
    if (this.name === 'approval-role' || this.name === 'wsd-selector') this.value = children[0]?.value ?? '';
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

async function harness({ stepUpAcr = 'urn:enterprise:mfa', receiptDigest = digest } = {}) {
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
    if (url === '/portal/token') return json({ access_token: 'opaque', token_type: 'Bearer' });
    if (url === '/v1/access/scopes') return json({ items: [] });
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
  async function authenticate(forApproval) {
    await context.signIn(forApproval);
    const popup = popups.at(-1);
    const params = new URL(popup.authUrl).searchParams;
    await context.receiveAuthorization({ origin, source: popup, data: {
      kind: 'mobility-oidc-response', state: params.get('state'), issuer,
      code: 'code12345', error: null
    } });
    return params;
  }
  return { context, element, authenticate, approvalRequests };
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
