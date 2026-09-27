'use strict';

const $ = (id) => document.getElementById(id);
const idPattern = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const digestPattern = /^[0-9a-f]{64}$/;
const approvalRoles = new Set(['SOURCE_OWNER', 'DESTINATION_OWNER', 'SOURCE_SECURITY', 'DESTINATION_SECURITY']);
let config = null;
let accessToken = null;
let expiryTimer = null;
let pending = null;
let tokenVersion = 0;
let stepUpRequested = false;
let activeWsd = null;
let workloadCursor = null;
let workloadRequest = 0;
let activeJob = null;
let eventCursor = 0;
let eventHasMore = false;
let jobRequest = 0;
let eventRequest = 0;
let reviewedPlan = null;
let reviewRequest = 0;
let approvalBusy = false;
let approvalSubmitted = false;

function announce(message, error = false) {
  $('page-error').hidden = !error;
  $('page-error').textContent = error ? message : '';
  $('session-status').textContent = message;
}

function clearSession(message = 'This tab has no active token.') {
  accessToken = null;
  tokenVersion++;
  stepUpRequested = false;
  if (expiryTimer) clearTimeout(expiryTimer);
  expiryTimer = null;
  if (pending?.popup && !pending.popup.closed) pending.popup.close();
  pending = null;
  activeWsd = null;
  activeJob = null;
  workloadCursor = null;
  workloadRequest++;
  eventCursor = 0;
  eventHasMore = false;
  jobRequest++;
  eventRequest++;
  $('workload-rows').replaceChildren();
  $('wsd-selector').replaceChildren(new Option('Choose a WSD', ''));
  $('wsd-selector').disabled = true;
  $('job-events').replaceChildren();
  $('job-details').hidden = true;
  $('load-more').hidden = true;
  $('more-events').hidden = true;
  $('refresh-job').disabled = true;
  $('clear-session').disabled = true;
  $('sign-in').disabled = !config;
  $('workload-status').textContent = 'Sign in to load workloads.';
  $('job-status').textContent = 'Sign in to load a job.';
  clearReview('Sign in to review a plan.');
  announce(message);
}

function clearReview(message = 'Load the current plan review before deciding.') {
  reviewedPlan = null;
  reviewRequest++;
  approvalBusy = false;
  approvalSubmitted = false;
  $('review-details').hidden = true;
  $('review-identity').replaceChildren();
  $('review-limits').replaceChildren();
  $('review-source').replaceChildren();
  $('review-destination').replaceChildren();
  $('approval-panel').hidden = true;
  $('approval-role').replaceChildren(new Option('Choose a role', ''));
  $('approval-role').disabled = true;
  $('approval-confirm').checked = false;
  $('approval-confirm').disabled = true;
  $('approve').disabled = true;
  $('review-status').textContent = message;
}

function randomBase64Url(bytes = 32) {
  const raw = crypto.getRandomValues(new Uint8Array(bytes));
  return btoa(String.fromCharCode(...raw)).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}

async function challengeFor(verifier) {
  const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
  return btoa(String.fromCharCode(...new Uint8Array(hash))).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}

async function signIn(forApproval = false) {
  if (!config) return;
  if (forApproval && !config.stepUpAcr) return;
  if (pending && !pending.popup.closed) {
    pending.popup.focus();
    return;
  }
  pending = null;
  if (forApproval) clearSession('Reauthenticate with enterprise identity, then load the plan review again.');
  const popup = window.open('about:blank', '_blank', 'popup,width=560,height=720');
  if (!popup) {
    announce('Allow the sign-in popup and try again.', true);
    return;
  }
  const state = randomBase64Url();
  const verifier = randomBase64Url();
  const nonce = randomBase64Url();
  // A new login supersedes any code exchange still in flight for this tab.
  tokenVersion++;
  pending = { popup, state, verifier, started: Date.now(), forApproval };
  const attempt = pending;
  setTimeout(() => {
    if (pending !== attempt) return;
    if (!popup.closed) popup.close();
    pending = null;
    announce('Sign-in timed out. Please try again.', true);
  }, 5 * 60 * 1000);
  try {
    const challenge = await challengeFor(verifier);
    if (pending !== attempt) return;
    const url = new URL(config.authorizeUrl);
    url.searchParams.set('response_type', 'code');
    url.searchParams.set('response_mode', 'form_post');
    url.searchParams.set('client_id', config.clientId);
    url.searchParams.set('redirect_uri', config.redirectUri);
    url.searchParams.set('scope', config.scope);
    url.searchParams.set('audience', config.audience);
    url.searchParams.set('state', state);
    url.searchParams.set('nonce', nonce);
    url.searchParams.set('code_challenge', challenge);
    url.searchParams.set('code_challenge_method', 'S256');
    if (forApproval) {
      url.searchParams.set('acr_values', config.stepUpAcr);
      url.searchParams.set('max_age', '0');
      url.searchParams.set('prompt', 'login');
    }
    popup.location.replace(url.href);
    announce('Complete enterprise sign-in in the popup.');
  } catch (_) {
    if (pending !== attempt) return;
    popup.close();
    pending = null;
    announce('Could not start enterprise sign-in.', true);
  }
}

async function receiveAuthorization(event) {
  if (!pending || !config || event.origin !== config.origin || event.source !== pending.popup) return;
  const data = event.data;
  if (!data || data.kind !== 'mobility-oidc-response' || data.state !== pending.state || data.issuer !== config.issuer) return;
  const { verifier, popup, started, forApproval } = pending;
  pending = null;
  const exchangeVersion = tokenVersion;
  if (!popup.closed) popup.close();
  if (Date.now() - started > 5 * 60 * 1000) {
    announce('Sign-in timed out. Please try again.', true);
    return;
  }
  if (data.error || typeof data.code !== 'string' || !data.code) {
    announce('Enterprise sign-in was not completed.', true);
    return;
  }
  try {
    const response = await fetch('/portal/token', {
      method: 'POST', credentials: 'omit', cache: 'no-store',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: data.code, verifier })
    });
    if (!response.ok) throw new Error('exchange');
    const result = await response.json();
    if (tokenVersion !== exchangeVersion) return;
    if (result.token_type !== 'Bearer' || typeof result.access_token !== 'string' || !result.access_token) throw new Error('token');
    if (expiryTimer) clearTimeout(expiryTimer);
    accessToken = result.access_token;
    tokenVersion++;
    stepUpRequested = forApproval;
    if (Number.isInteger(result.expires_in) && result.expires_in > 0) {
      expiryTimer = setTimeout(() => clearSession('Token expired. Sign in again.'),
        Math.max(1, result.expires_in - 30) * 1000);
    }
    $('clear-session').disabled = false;
    $('sign-in').disabled = true;
    announce(forApproval
      ? 'Reauthenticated token acquired. Reload the exact plan review; the server will verify step-up on approval.'
      : 'Token acquired for this tab. Enter a WSD, job or plan ID to load records.');
    await loadScopes();
  } catch (_) {
    if (tokenVersion !== exchangeVersion) return;
    clearSession('Enterprise sign-in failed. Please try again.');
    $('page-error').hidden = false;
    $('page-error').textContent = 'The identity provider did not complete the code exchange.';
  }
}

async function apiGet(path) {
  if (!accessToken) throw new Error('Sign in first.');
  const credential = accessToken;
  const version = tokenVersion;
  const response = await fetch(path, {
    method: 'GET', credentials: 'omit', cache: 'no-store',
    headers: { Authorization: `Bearer ${credential}`, Accept: 'application/json' }
  });
  if (tokenVersion !== version || accessToken !== credential) throw new Error('Identity changed. Load again.');
  if (response.status === 401) {
    clearSession('Token rejected or expired. Sign in again.');
    throw new Error('Token rejected or expired.');
  }
  if (response.status === 404) throw new Error('Record unavailable or outside your authorized scope.');
  if (!response.ok) throw new Error(`The API returned HTTP ${response.status}.`);
  const result = await response.json();
  if (tokenVersion !== version || accessToken !== credential) throw new Error('Identity changed. Load again.');
  return result;
}

async function apiPost(path, body) {
  if (!accessToken) throw new Error('Sign in first.');
  const credential = accessToken;
  const version = tokenVersion;
  let response;
  try {
    response = await fetch(path, {
      method: 'POST', credentials: 'omit', cache: 'no-store',
      headers: { Authorization: `Bearer ${credential}`, Accept: 'application/json',
        'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
  } catch (_) {
    if (tokenVersion !== version || accessToken !== credential) throw new Error('Identity changed. Load again.');
    const error = new Error('Approval result is unknown. Check the approval audit before retrying.');
    error.unknown = true;
    throw error;
  }
  if (tokenVersion !== version || accessToken !== credential) throw new Error('Identity changed. Load again.');
  if (response.status === 401) {
    clearSession('Token rejected or expired. Sign in again.');
    throw new Error('Token rejected or expired.');
  }
  if (response.status === 409) {
    const error = new Error('The plan changed. Load the current review before deciding.');
    error.stale = true;
    throw error;
  }
  if (response.status === 403) throw new Error('Approval denied. Check your role and recent enterprise step-up.');
  if (!response.ok) {
    const error = new Error('Approval result is unknown. Check the approval audit before retrying.');
    error.unknown = true;
    throw error;
  }
  try {
    const result = await response.json();
    if (tokenVersion !== version || accessToken !== credential) throw new Error('Identity changed. Load again.');
    return result;
  } catch (_) {
    if (tokenVersion !== version || accessToken !== credential) throw new Error('Identity changed. Load again.');
    const error = new Error('Approval result is unknown. Check the approval audit before retrying.');
    error.unknown = true;
    throw error;
  }
}

async function loadScopes() {
  const version = tokenVersion;
  try {
    const scopes = await apiGet('/v1/access/scopes');
    if (tokenVersion !== version) return;
    const ids = [...new Set(scopes.items
      .filter((item) => item.kind === 'PORTFOLIO' && item.role === 'WORKLOAD_READER')
      .map((item) => item.securityDomainId))].filter((id) => idPattern.test(id)).sort();
    $('wsd-selector').replaceChildren(new Option('Choose a WSD', ''));
    for (const id of ids) $('wsd-selector').add(new Option(id, id));
    $('wsd-selector').disabled = ids.length === 0;
    $('workload-status').textContent = ids.length
      ? `${ids.length} WSD read selector(s) available. Choose one to load recorded workloads.`
      : 'No WSD read grants were returned for this identity.';
  } catch (error) {
    if (tokenVersion !== version) return;
    $('workload-status').textContent = error.message;
  }
}

function textCell(row, value) {
  const cell = document.createElement('td');
  cell.textContent = String(value ?? 'Unknown');
  row.append(cell);
}

async function loadWorkloads(reset = false) {
  const wsd = $('wsd-id').value.trim();
  if (!idPattern.test(wsd)) {
    $('workload-status').textContent = 'Enter a valid WSD ID.';
    return;
  }
  if (reset || activeWsd !== wsd) {
    activeWsd = wsd;
    workloadCursor = null;
    $('workload-rows').replaceChildren();
    $('load-more').hidden = true;
  }
  $('workload-status').textContent = 'Loading recorded workloads…';
  const cursor = workloadCursor;
  const requestNumber = ++workloadRequest;
  try {
    const query = cursor ? `?limit=50&after=${encodeURIComponent(cursor)}` : '?limit=50';
    const page = await apiGet(`/v1/wsds/${encodeURIComponent(wsd)}/workloads${query}`);
    if (activeWsd !== wsd || workloadCursor !== cursor || !accessToken || requestNumber !== workloadRequest) return;
    for (const item of page.items) {
      const row = document.createElement('tr');
      const record = item.record;
      textCell(row, record.spec?.name);
      textCell(row, record.metadata?.workloadId);
      textCell(row, record.spec?.state);
      textCell(row, record.spec?.machines?.length);
      textCell(row, item.revision);
      $('workload-rows').append(row);
    }
    workloadCursor = page.nextAfter;
    $('load-more').hidden = !workloadCursor;
    $('workload-status').textContent = page.items.length
      ? `Showing ${$('workload-rows').childElementCount} recorded workload(s) in ${wsd}.`
      : 'No workloads were returned for this WSD.';
  } catch (error) {
    if (requestNumber === workloadRequest) $('workload-status').textContent = error.message;
  }
}

function displayTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Unknown' : date.toLocaleString();
}

async function loadJob(reset = false) {
  const jobId = $('job-id').value.trim();
  if (!idPattern.test(jobId)) {
    $('job-status').textContent = 'Enter a valid job ID.';
    return;
  }
  if (reset || activeJob !== jobId) {
    activeJob = jobId;
    eventCursor = 0;
    eventHasMore = false;
    $('job-events').replaceChildren();
    $('job-details').hidden = true;
    $('more-events').hidden = true;
  }
  $('job-status').textContent = 'Loading recorded job activity…';
  const requestNumber = ++jobRequest;
  try {
    const job = await apiGet(`/v1/jobs/${encodeURIComponent(jobId)}`);
    if (activeJob !== jobId || !accessToken || requestNumber !== jobRequest) return;
    $('job-state').textContent = job.status;
    $('job-plan').textContent = `${job.planId} · revision ${job.planRevision}`;
    $('job-updated').textContent = displayTime(job.updatedAt);
    $('job-details').hidden = false;
    $('refresh-job').disabled = false;
    await loadEvents();
    $('job-status').textContent = `Last recorded event sequence: ${job.lastEventSequence}.`;
  } catch (error) {
    if (requestNumber === jobRequest) {
      $('job-status').textContent = error.message;
      $('job-details').hidden = true;
    }
  }
}

async function loadEvents() {
  if (!activeJob) return;
  const jobId = activeJob;
  const cursor = eventCursor;
  const requestNumber = ++eventRequest;
  const page = await apiGet(`/v1/jobs/${encodeURIComponent(jobId)}/events?after=${cursor}&limit=50`);
  if (activeJob !== jobId || eventCursor !== cursor || !accessToken || requestNumber !== eventRequest) return;
  for (const event of page.items) {
    const item = document.createElement('li');
    const label = document.createElement('strong');
    label.textContent = `${event.sequence}. ${event.eventType} · ${event.status}`;
    const time = document.createElement('small');
    time.textContent = displayTime(event.recordedAt);
    item.append(label, time);
    $('job-events').append(item);
  }
  eventCursor = page.items.length ? page.items[page.items.length - 1].sequence : cursor;
  eventHasMore = page.nextAfter !== null;
  $('more-events').hidden = !eventHasMore;
}

function addFact(container, label, value) {
  const row = document.createElement('div');
  const term = document.createElement('dt');
  const description = document.createElement('dd');
  term.textContent = label;
  description.textContent = String(value ?? 'Unknown');
  row.append(term, description);
  container.append(row);
}

function validReview(plan, requestedId) {
  const scopeFields = ['organizationId', 'tenantId', 'siteId', 'securityDomainId',
    'endpointId', 'nativeScopeId', 'platformFamily'];
  const scopeValid = (scope) => scope && typeof scope === 'object' &&
    scopeFields.every((key) => typeof scope[key] === 'string' && scope[key].length > 0);
  return plan && plan.planId === requestedId && Number.isInteger(plan.planRevision) &&
    plan.planRevision > 0 && digestPattern.test(plan.planDigest) &&
    typeof plan.workloadId === 'string' && Number.isInteger(plan.workloadRevision) &&
    typeof plan.routeMethod === 'string' && plan.routeMethod.length > 0 &&
    typeof plan.frozenAt === 'string' && scopeValid(plan.source) && scopeValid(plan.destination) &&
    ['selectedMachineCount', 'selectedDatasetCount', 'maxDowntimeSeconds',
      'maxDataLossSeconds', 'rollbackWindowSeconds'].every((key) =>
      Number.isInteger(plan[key]) && plan[key] >= 0) &&
    Array.isArray(plan.eligibleRoles) && plan.eligibleRoles.every((role) => approvalRoles.has(role));
}

function displayReview(plan) {
  addFact($('review-identity'), 'Plan ID', plan.planId);
  addFact($('review-identity'), 'Revision', plan.planRevision);
  addFact($('review-identity'), 'Full digest', plan.planDigest);
  addFact($('review-identity'), 'Frozen at', plan.frozenAt);
  addFact($('review-identity'), 'Workload ID', plan.workloadId);
  addFact($('review-identity'), 'Workload revision', plan.workloadRevision);
  addFact($('review-identity'), 'Route method', plan.routeMethod);
  if (plan.sourceSnapshotId) addFact($('review-identity'), 'Source snapshot', plan.sourceSnapshotId);
  if (plan.destinationSnapshotId) addFact($('review-identity'), 'Destination snapshot', plan.destinationSnapshotId);
  addFact($('review-limits'), 'Selected machines', plan.selectedMachineCount);
  addFact($('review-limits'), 'Selected datasets', plan.selectedDatasetCount);
  addFact($('review-limits'), 'Maximum allowed downtime', `${plan.maxDowntimeSeconds} seconds`);
  addFact($('review-limits'), 'Maximum allowed data loss', `${plan.maxDataLossSeconds} seconds`);
  addFact($('review-limits'), 'Rollback window', `${plan.rollbackWindowSeconds} seconds`);
  const scopeLabels = {
    organizationId: 'Organization', tenantId: 'Tenant', siteId: 'Site',
    securityDomainId: 'Security domain', endpointId: 'Endpoint',
    nativeScopeId: 'Native scope', platformFamily: 'Platform'
  };
  for (const [key, label] of Object.entries(scopeLabels)) {
    addFact($('review-source'), label, plan.source[key]);
    addFact($('review-destination'), label, plan.destination[key]);
  }
  $('review-details').hidden = false;
}

function updateApprovalControls() {
  const role = $('approval-role').value;
  const minutes = Number($('approval-ttl').value);
  const ready = reviewedPlan && reviewedPlan.tokenVersion === tokenVersion &&
    stepUpRequested && !approvalBusy && !approvalSubmitted &&
    reviewedPlan.eligibleRoles.includes(role) &&
    Number.isInteger(minutes) && minutes >= 1 && minutes <= 480 &&
    $('approval-confirm').checked && $('plan-id').value.trim() === reviewedPlan.planId;
  $('approve').disabled = !ready;
}

async function loadReview() {
  const planId = $('plan-id').value.trim();
  clearReview('Loading the current, scoped plan review…');
  if (!idPattern.test(planId)) {
    $('review-status').textContent = 'Enter a valid plan ID.';
    return;
  }
  const requestNumber = reviewRequest;
  const currentTokenVersion = tokenVersion;
  try {
    const plan = await apiGet(`/v1/plans/${encodeURIComponent(planId)}/review`);
    if (requestNumber !== reviewRequest || currentTokenVersion !== tokenVersion) return;
    if (!validReview(plan, planId)) throw new Error('The API returned an incomplete plan review. Approval is unavailable.');
    reviewedPlan = { ...plan, tokenVersion };
    displayReview(plan);
    $('review-status').textContent = `Current plan revision ${plan.planRevision}, digest ${plan.planDigest}.`;
    if (!config?.stepUpAcr) {
      $('approval-status').textContent = 'Approval is unavailable: enterprise step-up is not configured for this portal.';
      return;
    }
    $('approval-panel').hidden = false;
    $('approval-role').replaceChildren(new Option('Choose a role', ''));
    for (const role of [...new Set(plan.eligibleRoles)]) $('approval-role').add(new Option(role.replaceAll('_', ' '), role));
    $('approval-role').disabled = !stepUpRequested || plan.eligibleRoles.length === 0;
    $('approval-confirm').disabled = !stepUpRequested || plan.eligibleRoles.length === 0;
    $('approval-status').textContent = stepUpRequested
      ? (plan.eligibleRoles.length
        ? 'Step-up was requested. Review these exact values, then select your role. The server verifies step-up and scope.'
        : 'No approval role is available for this identity and plan.')
      : 'Reauthenticate for approval, then load this plan review again under the new token.';
    updateApprovalControls();
  } catch (error) {
    if (requestNumber === reviewRequest) $('review-status').textContent = error.message;
  }
}

async function recordApproval() {
  updateApprovalControls();
  if ($('approve').disabled || !reviewedPlan) return;
  const plan = reviewedPlan;
  const role = $('approval-role').value;
  const ttlSeconds = Number($('approval-ttl').value) * 60;
  const currentTokenVersion = tokenVersion;
  approvalBusy = true;
  updateApprovalControls();
  $('approval-status').textContent = 'Submitting an approval bound to the reviewed revision and digest…';
  try {
    const receipt = await apiPost(`/v1/plans/${encodeURIComponent(plan.planId)}/approvals`, {
      role, ttlSeconds, expectedPlanRevision: plan.planRevision,
      expectedPlanDigest: plan.planDigest
    });
    if (reviewedPlan !== plan || currentTokenVersion !== tokenVersion) {
      $('approval-status').textContent = 'Approval response arrived after this review changed. Check the approval audit.';
      return;
    }
    if (receipt.planId !== plan.planId || receipt.planRevision !== plan.planRevision ||
        receipt.planDigest !== plan.planDigest || receipt.role !== role ||
        typeof receipt.approvalId !== 'string' || !receipt.approvalId) {
      approvalSubmitted = true;
      $('approval-status').textContent = 'Approval receipt differs from the reviewed plan. Contact an operator and check the approval audit.';
      return;
    }
    approvalSubmitted = true;
    $('approval-status').textContent = `Approval ${receipt.approvalId} recorded for ${role}, revision ${receipt.planRevision}, digest ${receipt.planDigest}; expires ${receipt.expiresAt}.`;
  } catch (error) {
    if (reviewedPlan !== plan || currentTokenVersion !== tokenVersion) return;
    if (error.stale) {
      clearReview(error.message);
      return;
    }
    $('approval-status').textContent = error.message;
    if (error.unknown) approvalSubmitted = true;
  } finally {
    if (reviewedPlan === plan && currentTokenVersion === tokenVersion) {
      approvalBusy = false;
      updateApprovalControls();
    }
  }
}

window.addEventListener('message', receiveAuthorization);
$('sign-in').addEventListener('click', () => signIn(false));
$('clear-session').addEventListener('click', () => clearSession());
$('workload-form').addEventListener('submit', (event) => {
  event.preventDefault();
  loadWorkloads(true);
});
$('wsd-selector').addEventListener('change', (event) => {
  if (event.target.value) $('wsd-id').value = event.target.value;
});
$('load-more').addEventListener('click', () => loadWorkloads());
$('job-form').addEventListener('submit', (event) => {
  event.preventDefault();
  loadJob(true);
});
$('refresh-job').addEventListener('click', () => loadJob());
$('more-events').addEventListener('click', async () => {
  const version = tokenVersion;
  const jobId = activeJob;
  try { await loadEvents(); } catch (error) {
    if (version === tokenVersion && jobId === activeJob) $('job-status').textContent = error.message;
  }
});
$('review-form').addEventListener('submit', (event) => {
  event.preventDefault();
  loadReview();
});
$('step-up').addEventListener('click', () => signIn(true));
$('approval-role').addEventListener('change', updateApprovalControls);
$('approval-ttl').addEventListener('input', updateApprovalControls);
$('approval-confirm').addEventListener('change', updateApprovalControls);
$('plan-id').addEventListener('input', updateApprovalControls);
$('approval-form').addEventListener('submit', (event) => {
  event.preventDefault();
  recordApproval();
});

(async () => {
  try {
    const response = await fetch('/portal/config.json', { credentials: 'omit', cache: 'no-store' });
    if (!response.ok) throw new Error('unavailable');
    const configured = await response.json();
    if (configured.origin !== window.location.origin || configured.redirectUri !== `${configured.origin}/portal/callback`) throw new Error('origin');
    config = configured;
    $('sign-in').disabled = false;
    announce('Sign in with enterprise identity.');
  } catch (_) {
    announce('Portal identity configuration is unavailable.', true);
  }
})();
