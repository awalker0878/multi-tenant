'use strict';

const $ = (id) => document.getElementById(id);
const idPattern = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const digestPattern = /^[0-9a-f]{64}$/;
const approvalRoles = new Set(['SOURCE_OWNER', 'DESTINATION_OWNER', 'SOURCE_SECURITY', 'DESTINATION_SECURITY']);
let applicationDraftWorkspace = null;
let config = null;
let accessToken = null;
let expiryTimer = null;
let pending = null;
let tokenVersion = 0;
let stepUpRequested = false;
let activeWsd = null;
let workloadCursor = null;
let workloadRequest = 0;
let environmentWsd = null;
let environmentCursor = null;
let environmentRequest = 0;
let discoveryEnvironment = null;
let discoveryGeneration = null;
let discoveryCursor = null;
let discoveryRequest = 0;
let discoveryObjectRequest = 0;
let observedVms = new Set();
let comparisonDestinations = [];
let destinationOptions = new Map();
let destinationWsd = null;
let destinationCursor = null;
let destinationRequest = 0;
let destinationAddRequest = 0;
let comparisonRequest = 0;
let comparisonBusy = false;
const assessmentMethods = new Set(['REBUILD_RESTORE', 'COLD_VM_CONVERSION',
  'SAME_PLATFORM_RELOCATION', 'APPLICATION_NATIVE', 'WARM_VM_TRANSFER']);
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
  applicationDraftWorkspace?.clear();
  accessToken = null;
  tokenVersion++;
  stepUpRequested = false;
  if (expiryTimer) clearTimeout(expiryTimer);
  expiryTimer = null;
  if (pending?.popup && !pending.popup.closed) pending.popup.close();
  pending = null;
  activeWsd = null;
  environmentWsd = null;
  activeJob = null;
  workloadCursor = null;
  workloadRequest++;
  environmentCursor = null;
  environmentRequest++;
  clearDiscovery('Sign in and load environment declarations to select a source.');
  clearDestinationDirectory();
  $('discovery-environment').replaceChildren(new Option('Choose an environment', ''));
  $('discovery-environment').disabled = true;
  $('show-discovery').disabled = true;
  $('environment-rows').replaceChildren();
  $('environment-selector').replaceChildren(new Option('Choose a WSD', ''));
  $('environment-selector').disabled = true;
  $('more-environments').hidden = true;
  $('environment-status').textContent = 'Sign in to load environment declarations.';
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

function clearDiscovery(message = 'Choose an authorized environment to load observations.') {
  discoveryEnvironment = null;
  discoveryGeneration = null;
  discoveryCursor = null;
  discoveryRequest++;
  discoveryObjectRequest++;
  clearAssessmentSource();
  $('discovery-rows').replaceChildren();
  $('discovery-details').hidden = true;
  $('more-discovery').hidden = true;
  $('discovery-status').textContent = message;
}

function updateComparisonControls() {
  const sourceReady = Boolean(accessToken && discoveryEnvironment && discoveryGeneration &&
    observedVms.has($('comparison-workload').value));
  $('compare-destinations').disabled = comparisonBusy || !sourceReady || comparisonDestinations.length < 2;
  $('add-destination').disabled = !accessToken || !discoveryGeneration ||
    !destinationOptions.has($('destination-environment').value) || comparisonDestinations.length >= 20;
}

function invalidateComparison(message = 'Choose an observed VM and at least two destinations.') {
  comparisonRequest++;
  comparisonBusy = false;
  $('comparison-results').replaceChildren();
  $('comparison-results').hidden = true;
  $('comparison-status').textContent = message;
  updateComparisonControls();
}

function clearAssessmentSource() {
  observedVms = new Set();
  comparisonDestinations = [];
  destinationAddRequest++;
  $('comparison-workload').replaceChildren(new Option('Choose an observed VM', ''));
  $('comparison-workload').disabled = true;
  $('comparison-source').textContent = 'Load source observations first.';
  $('destination-rows').replaceChildren();
  invalidateComparison();
}

function clearDestinationDirectory() {
  destinationRequest++;
  destinationAddRequest++;
  destinationOptions = new Map();
  destinationWsd = null;
  destinationCursor = null;
  $('destination-wsd').replaceChildren(new Option('Choose an authorized WSD', ''));
  $('destination-wsd').disabled = true;
  $('show-destinations').disabled = true;
  $('destination-environment').replaceChildren(new Option('Choose an environment', ''));
  $('destination-environment').disabled = true;
  $('more-destinations').hidden = true;
  $('destination-status').textContent = 'Sign in to choose authorized destinations.';
  updateComparisonControls();
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
  applicationDraftWorkspace?.clear();
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
    clearAssessmentSource();
    clearDestinationDirectory();
    applicationDraftWorkspace?.clear();
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
  if (response.status === 404) {
    const error = new Error('Record unavailable or outside your authorized scope.');
    error.notFound = true;
    throw error;
  }
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
    const environmentIds = [...new Set(scopes.items
      .filter((item) => item.kind === 'NATIVE' &&
        ['JOB_READER', 'EXECUTION_OPERATOR'].includes(item.role))
      .map((item) => item.securityDomainId))].filter((id) => idPattern.test(id)).sort();
    $('environment-selector').replaceChildren(new Option('Choose a WSD', ''));
    for (const id of environmentIds) $('environment-selector').add(new Option(id, id));
    $('environment-selector').disabled = environmentIds.length === 0;
    $('destination-wsd').replaceChildren(new Option('Choose an authorized WSD', ''));
    for (const id of environmentIds) $('destination-wsd').add(new Option(id, id));
    $('destination-wsd').disabled = environmentIds.length === 0;
    $('show-destinations').disabled = environmentIds.length === 0;
    $('destination-status').textContent = environmentIds.length
      ? 'Choose an authorized WSD to find destination environments.'
      : 'No exact native read grants were returned for destination environments.';
    $('environment-status').textContent = environmentIds.length
      ? `${environmentIds.length} WSD declaration selector(s) available.`
      : 'No exact native read grants were returned for environment declarations.';
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

async function loadEnvironments(reset = false) {
  const wsd = $('environment-wsd').value.trim();
  if (!idPattern.test(wsd)) {
    $('environment-status').textContent = 'Enter a valid WSD ID.';
    return;
  }
  if (reset || environmentWsd !== wsd) {
    environmentWsd = wsd;
    environmentCursor = null;
    $('environment-rows').replaceChildren();
    $('more-environments').hidden = true;
    clearDiscovery();
    $('discovery-environment').replaceChildren(new Option('Choose an environment', ''));
    $('discovery-environment').disabled = true;
    $('show-discovery').disabled = true;
  }
  const cursor = environmentCursor;
  const requestNumber = ++environmentRequest;
  $('environment-status').textContent = 'Loading authorized declarations…';
  try {
    const query = `?wsdId=${encodeURIComponent(wsd)}&limit=50` +
      (cursor ? `&after=${encodeURIComponent(cursor)}` : '');
    const page = await apiGet('/v1/environments' + query);
    if (environmentWsd !== wsd || environmentCursor !== cursor ||
        !accessToken || requestNumber !== environmentRequest) return;
    for (const item of page.items) {
      if (item.securityDomainId !== wsd || item.status !== 'DECLARED_UNVERIFIED') {
        throw new Error('The API returned an inconsistent environment declaration.');
      }
      const row = document.createElement('tr');
      for (const field of ['displayName', 'environmentId', 'siteId', 'platformFamily',
        'endpointId', 'nativeScopeId', 'status']) textCell(row, item[field]);
      $('environment-rows').append(row);
      if (!idPattern.test(item.environmentId)) throw new Error('Invalid environment identity.');
      $('discovery-environment').add(new Option(
        `${item.displayName} · ${item.environmentId} · ${item.platformFamily}`,
        item.environmentId));
    }
    $('discovery-environment').disabled = $('discovery-environment').children.length <= 1;
    $('show-discovery').disabled = $('discovery-environment').disabled;
    environmentCursor = page.nextAfter;
    $('more-environments').hidden = !environmentCursor;
    $('environment-status').textContent = `${$('environment-rows').childElementCount} unverified declaration(s) in ${wsd}.`;
  } catch (error) {
    if (requestNumber === environmentRequest) $('environment-status').textContent = error.message;
  }
}

function discoveryCoverage(completeness) {
  if (completeness === 'COMPLETE') return 'Reported complete page chain; native visibility unverified';
  if (completeness === 'PARTIAL') return 'Partial; inventory gaps present';
  return 'Unknown; inventory coverage unverified';
}

async function loadDiscovery() {
  const environmentId = $('discovery-environment').value;
  clearDiscovery('Loading the latest recorded observation…');
  if (!idPattern.test(environmentId) || $('discovery-environment').disabled) {
    $('discovery-status').textContent = 'Choose an authorized environment declaration.';
    return;
  }
  discoveryEnvironment = environmentId;
  const requestNumber = ++discoveryRequest;
  try {
    const page = await apiGet(`/v1/environments/${encodeURIComponent(environmentId)}/discovery/generations/latest`);
    if (discoveryEnvironment !== environmentId || requestNumber !== discoveryRequest || !accessToken) return;
    if (page.environmentId !== environmentId || !Number.isSafeInteger(page.generation) ||
        page.generation < 1 || !['COMPLETE', 'PARTIAL', 'UNKNOWN'].includes(page.completeness) ||
        !digestPattern.test(page.resultDigest) ||
        !['objectCount', 'collectionErrorCount', 'missingPrivilegeCount'].every((key) =>
          Number.isInteger(page[key]) && page[key] >= 0) ||
        (page.completeness === 'COMPLETE' &&
          (page.collectionErrorCount > 0 || page.missingPrivilegeCount > 0))) {
      throw new Error('The observation summary does not match this environment.');
    }
    discoveryGeneration = page.generation;
    $('comparison-source').textContent = `${environmentId} · observed generation ${page.generation}`;
    $('discovery-generation').textContent = String(page.generation);
    $('discovery-completeness').textContent = discoveryCoverage(page.completeness);
    $('discovery-captured').textContent = displayTime(page.capturedAt);
    $('discovery-count').textContent = String(page.objectCount);
    $('discovery-errors').textContent = String(page.collectionErrorCount);
    $('discovery-privileges').textContent = String(page.missingPrivilegeCount);
    $('discovery-details').hidden = false;
    $('discovery-status').textContent = `Generation ${page.generation}: ${discoveryCoverage(page.completeness)}. Identity summaries only; no native qualification or execution approval.`;
    await loadObservedObjects();
  } catch (error) {
    if (requestNumber === discoveryRequest && discoveryEnvironment === environmentId) {
      $('discovery-status').textContent = error.notFound
        ? 'No observation is available for this environment under your current access.'
        : error.message;
      $('discovery-details').hidden = true;
      $('discovery-rows').replaceChildren();
      $('more-discovery').hidden = true;
    }
  }
}

async function loadObservedObjects() {
  if (!discoveryEnvironment || !discoveryGeneration) return;
  const environmentId = discoveryEnvironment;
  const generation = discoveryGeneration;
  const cursor = discoveryCursor;
  const requestNumber = ++discoveryObjectRequest;
  try {
    const query = '?limit=50' + (cursor ? `&after=${encodeURIComponent(cursor)}` : '');
    const page = await apiGet(`/v1/environments/${encodeURIComponent(environmentId)}/discovery/generations/${generation}/objects${query}`);
    if (discoveryEnvironment !== environmentId || discoveryGeneration !== generation ||
        discoveryCursor !== cursor || requestNumber !== discoveryObjectRequest || !accessToken) return;
    if (page.environmentId !== environmentId || page.generation !== generation ||
        !Array.isArray(page.items) || page.items.length > 50 ||
        (page.nextAfter !== null && (typeof page.nextAfter !== 'string' ||
          page.nextAfter.length === 0 || page.nextAfter === cursor))) {
      throw new Error('The observation page changed while loading.');
    }
    for (const item of page.items) {
      if (typeof item.resourceKind !== 'string' || typeof item.nativeId !== 'string' ||
          !Number.isInteger(item.unknownCount) || item.unknownCount < 0 ||
          (item.displayName !== null && typeof item.displayName !== 'string')) {
        throw new Error('The API returned an invalid identity summary.');
      }
      const row = document.createElement('tr');
      for (const value of [item.resourceKind, item.nativeId,
        item.displayName ?? 'Unknown', item.unknownCount]) textCell(row, value);
      $('discovery-rows').append(row);
      if (item.resourceKind === 'vm' && nativeSelection(item.nativeId) && !observedVms.has(item.nativeId)) {
        observedVms.add(item.nativeId);
        $('comparison-workload').add(new Option(`${item.displayName ?? 'Unnamed VM'} · ${item.nativeId}`, item.nativeId));
      }
    }
    $('comparison-workload').disabled = observedVms.size === 0;
    updateComparisonControls();
    discoveryCursor = page.nextAfter;
    $('more-discovery').hidden = !discoveryCursor;
  } catch (error) {
    if (discoveryEnvironment === environmentId && discoveryGeneration === generation &&
        requestNumber === discoveryObjectRequest) {
      $('discovery-status').textContent = `Identity list is incomplete: ${error.message}`;
      $('discovery-rows').replaceChildren();
      $('more-discovery').hidden = true;
      discoveryCursor = null;
      clearAssessmentSource();
    }
  }
}

function nativeSelection(value) {
  return typeof value === 'string' && value.length > 0 && value.length <= 512 &&
    value.trim().length > 0 && !/[\u0000-\u001f\u007f]/.test(value);
}

async function loadDestinationEnvironments(reset = false) {
  const wsd = $('destination-wsd').value;
  if (!idPattern.test(wsd) || $('destination-wsd').disabled) return;
  invalidateComparison();
  destinationAddRequest++;
  if (reset || destinationWsd !== wsd) {
    destinationWsd = wsd;
    destinationCursor = null;
    destinationOptions = new Map();
    $('destination-environment').replaceChildren(new Option('Choose an environment', ''));
    $('destination-environment').disabled = true;
    $('more-destinations').hidden = true;
  }
  const cursor = destinationCursor;
  const requestNumber = ++destinationRequest;
  $('destination-status').textContent = 'Loading authorized destination declarations…';
  updateComparisonControls();
  try {
    const page = await apiGet('/v1/environments?wsdId=' + encodeURIComponent(wsd) + '&limit=50' +
      (cursor ? '&after=' + encodeURIComponent(cursor) : ''));
    if (!accessToken || requestNumber !== destinationRequest || destinationWsd !== wsd ||
        $('destination-wsd').value !== wsd || destinationCursor !== cursor) return;
    if (!Array.isArray(page.items) || page.items.length > 50 ||
        (page.nextAfter !== null && (!idPattern.test(page.nextAfter) || page.nextAfter === cursor)) ||
        page.items.some((item) => !idPattern.test(item.environmentId) ||
          item.securityDomainId !== wsd || item.status !== 'DECLARED_UNVERIFIED' ||
          typeof item.displayName !== 'string')) throw new Error('Invalid destination declaration page.');
    for (const item of page.items) {
      if (!destinationOptions.has(item.environmentId)) {
        destinationOptions.set(item.environmentId, item);
        $('destination-environment').add(new Option(`${item.displayName} · ${item.environmentId} · ${item.platformFamily}`, item.environmentId));
      }
    }
    $('destination-environment').disabled = destinationOptions.size === 0;
    destinationCursor = page.nextAfter;
    $('more-destinations').hidden = !destinationCursor;
    $('destination-status').textContent = `${destinationOptions.size} candidate declaration(s). Add a destination to pin its current observation.`;
    updateComparisonControls();
  } catch (error) {
    if (requestNumber === destinationRequest && destinationWsd === wsd) {
      $('destination-status').textContent = error.message;
    }
  }
}

function renderDestinations() {
  $('destination-rows').replaceChildren();
  for (const item of comparisonDestinations) {
    const row = document.createElement('tr');
    textCell(row, `${item.displayName} · ${item.environmentId}`);
    textCell(row, `${item.generation} · ${discoveryCoverage(item.completeness)}`);
    const capacity = document.createElement('td');
    const container = document.createElement('div');
    container.className = 'capacity-selection';
    const kindLabel = document.createElement('label');
    kindLabel.textContent = 'Capacity kind';
    const kind = document.createElement('select');
    kind.add(new Option('Not selected', ''));
    for (const value of ['pool', 'cluster', 'quota', 'datastore']) kind.add(new Option(value, value));
    kind.value = item.capacityKind ?? '';
    const nativeLabel = document.createElement('label');
    nativeLabel.textContent = 'Native capacity ID';
    const native = document.createElement('input');
    native.type = 'text';
    native.maxLength = 512;
    native.autocomplete = 'off';
    native.value = item.capacityNativeId ?? '';
    const changed = () => {
      item.capacityKind = kind.value;
      item.capacityNativeId = native.value;
      invalidateComparison('Capacity selection changed. Compare again to assess the selected identity.');
    };
    kind.addEventListener('change', changed);
    native.addEventListener('input', changed);
    kindLabel.append(kind);
    nativeLabel.append(native);
    container.append(kindLabel, nativeLabel);
    capacity.append(container);
    row.append(capacity);
    const action = document.createElement('td');
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'quiet';
    remove.textContent = 'Remove';
    remove.addEventListener('click', () => {
      comparisonDestinations = comparisonDestinations.filter((candidate) => candidate !== item);
      invalidateComparison();
      renderDestinations();
    });
    action.append(remove);
    row.append(action);
    $('destination-rows').append(row);
  }
  updateComparisonControls();
}

async function addDestination() {
  const environmentId = $('destination-environment').value;
  const candidate = destinationOptions.get(environmentId);
  invalidateComparison();
  if (!accessToken || !discoveryGeneration || !candidate) return;
  if (environmentId === discoveryEnvironment || comparisonDestinations.some((item) => item.environmentId === environmentId)) {
    $('destination-status').textContent = 'Choose a destination distinct from the source and existing selections.';
    return;
  }
  if (comparisonDestinations.length >= 20) return;
  const sourceEnvironment = discoveryEnvironment;
  const sourceGeneration = discoveryGeneration;
  const requestNumber = ++destinationAddRequest;
  $('destination-status').textContent = 'Loading the latest destination observation…';
  try {
    const page = await apiGet(`/v1/environments/${encodeURIComponent(environmentId)}/discovery/generations/latest`);
    if (!accessToken || requestNumber !== destinationAddRequest ||
        discoveryEnvironment !== sourceEnvironment || discoveryGeneration !== sourceGeneration ||
        $('destination-environment').value !== environmentId || destinationOptions.get(environmentId) !== candidate) return;
    if (page.environmentId !== environmentId || !Number.isSafeInteger(page.generation) || page.generation < 1 ||
        !['COMPLETE', 'PARTIAL', 'UNKNOWN'].includes(page.completeness) || !digestPattern.test(page.resultDigest) ||
        !['objectCount', 'collectionErrorCount', 'missingPrivilegeCount'].every((key) =>
          Number.isSafeInteger(page[key]) && page[key] >= 0) ||
        (page.completeness === 'COMPLETE' && (page.collectionErrorCount || page.missingPrivilegeCount))) {
      throw new Error('Destination observation does not match the selected environment.');
    }
    comparisonDestinations.push({ environmentId, generation: page.generation,
      displayName: candidate.displayName, completeness: page.completeness });
    invalidateComparison();
    renderDestinations();
    $('destination-status').textContent = `${environmentId} pinned at generation ${page.generation}. ${comparisonDestinations.length} destination(s) selected.`;
  } catch (error) {
    if (requestNumber === destinationAddRequest && discoveryEnvironment === sourceEnvironment) {
      $('destination-status').textContent = error.notFound
        ? 'No current observation is available for this destination under your access.' : error.message;
    }
  }
}

function comparisonBody() {
  if (!accessToken || !discoveryEnvironment || !Number.isSafeInteger(discoveryGeneration) ||
      !observedVms.has($('comparison-workload').value) || comparisonDestinations.length < 2 ||
      comparisonDestinations.length > 20) throw new Error('Choose an observed VM and between two and twenty distinct destinations.');
  const method = $('comparison-method').value;
  const guestProfile = $('comparison-guest').value.trim();
  const networkMode = $('comparison-network').value.trim();
  const dataMode = $('comparison-data').value.trim();
  if (!assessmentMethods.has(method) || ![guestProfile, networkMode, dataMode].every((value) => idPattern.test(value))) {
    throw new Error('Choose a migration method and enter the guest, network and data profile identifiers.');
  }
  const destinations = comparisonDestinations.map((item) => {
    const result = { environmentId: item.environmentId, generation: item.generation };
    if (item.capacityKind || item.capacityNativeId) {
      if (!['pool', 'cluster', 'quota', 'datastore'].includes(item.capacityKind) || !nativeSelection(item.capacityNativeId)) {
        throw new Error('Capacity selections require both an observed kind and its exact native identity.');
      }
      result.capacityKind = item.capacityKind;
      result.capacityNativeId = item.capacityNativeId;
    }
    return result;
  });
  return { source: { environmentId: discoveryEnvironment, generation: discoveryGeneration },
    workloadNativeId: $('comparison-workload').value, destinations, method, guestProfile, networkMode, dataMode };
}

async function requestComparison(body) {
  const credential = accessToken;
  const version = tokenVersion;
  if (!credential) throw new Error('Sign in first.');
  const response = await fetch('/v1/assessments/compare', {
    method: 'POST', credentials: 'omit', cache: 'no-store',
    headers: { Authorization: `Bearer ${credential}`, Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (tokenVersion !== version || accessToken !== credential) throw new Error('Identity changed. Load again.');
  if (response.status === 401) {
    clearSession('Token rejected or expired. Sign in again.');
    throw new Error('Token rejected or expired.');
  }
  if ([403, 404].includes(response.status)) throw new Error('Assessment unavailable under your current scope access.');
  if (response.status === 409) throw new Error('Assessment inputs changed or are unavailable. Reload observations and compare again.');
  if (response.status === 503) throw new Error('Verified assessment inputs are unavailable. No comparison was produced.');
  if (!response.ok) throw new Error(`Assessment could not be completed (HTTP ${response.status}).`);
  const result = await response.json();
  if (tokenVersion !== version || accessToken !== credential) throw new Error('Identity changed. Load again.');
  return result;
}

function validateComparison(result, body) {
  const currentMetadata = (binding) => {
    const latest = binding?.latestObservation;
    return latest && Number.isSafeInteger(latest.generation) && latest.generation > 0 &&
      typeof latest.rawSnapshotDigest === 'string' && /^[0-9a-f]{64}$/.test(latest.rawSnapshotDigest) &&
      typeof latest.capturedAt === 'string' && !Number.isNaN(Date.parse(latest.capturedAt)) &&
      ['COMPLETE', 'PARTIAL', 'UNKNOWN'].includes(latest.collectionCompleteness) &&
      ['collectionErrors', 'missingPrivileges'].every((key) => Array.isArray(latest[key]) &&
        latest[key].length <= 64 && latest[key].every((value) => typeof value === 'string')) &&
      binding.superseded === (latest.generation > binding.generation) &&
      (!binding.observation || (latest.generation >= binding.generation &&
        (latest.generation !== binding.generation || latest.rawSnapshotDigest === binding.observation.rawSnapshotDigest)));
  };
  const bound = (binding, selection) => binding && binding.environmentId === selection.environmentId &&
    binding.generation === selection.generation && typeof binding.endpointId === 'string' &&
    typeof binding.nativeScopeId === 'string' && typeof binding.platformFamily === 'string' && currentMetadata(binding);
  const installed = (tuple, binding) => tuple &&
    ['endpointId', 'nativeScopeId', 'platformFamily', 'productTupleId', 'productTupleDigest']
      .every((key) => typeof binding[key] === 'string' && tuple[key] === binding[key]);
  if (!result || result.format !== 'hosting-discovery-comparison/1' || result.executionAuthorized !== false ||
      !bound(result.sourceInput, body.source) || !Array.isArray(result.destinationInputs) ||
      result.destinationInputs.length !== body.destinations.length || !Array.isArray(result.assessments) ||
      result.assessments.length !== body.destinations.length || typeof result.assessedAt !== 'string') {
    throw new Error('The assessment response does not match the selected observations.');
  }
  for (let index = 0; index < body.destinations.length; index++) {
    const binding = result.destinationInputs[index];
    const item = result.assessments[index];
    if (!bound(binding, body.destinations[index]) || !item || item.format !== 'hosting-destination-assessment/1' ||
        item.executionAuthorized !== false || !installed(item.source, result.sourceInput) || !installed(item.destination, binding) ||
        !['ELIGIBLE', 'CONDITIONAL', 'BLOCKED', 'UNKNOWN'].includes(item.status) || typeof item.routeMaturity !== 'string' ||
        !item.workload || item.workload.nativeId !== body.workloadNativeId || item.workload.resourceKind !== 'vm' ||
        !['endpointId', 'nativeScopeId', 'platformFamily'].every((key) => item.workload[key] === result.sourceInput[key]) ||
        !['method', 'guestProfile', 'networkMode', 'dataMode'].every((key) => item[key] === body[key]) ||
        !Array.isArray(item.issues) || item.issues.length > 200 || item.issues.some((issue) =>
          !issue || !['BLOCKER', 'UNKNOWN', 'CONDITION'].includes(issue.severity) ||
          !['code', 'reason', 'remediation'].every((key) => typeof issue[key] === 'string' && issue[key].length > 0)) ||
        [[result.sourceInput, 'SOURCE'], [binding, 'DESTINATION']].some(([input, side]) =>
          input.superseded && (item.status !== 'UNKNOWN' || !item.issues.some((issue) =>
            issue.severity === 'UNKNOWN' && issue.code === `${side}_SNAPSHOT_SUPERSEDED`))) ||
        !item.estimate || !['NONE', 'LOW'].includes(item.estimate.confidence) ||
        !['transferBytes', 'copyPhaseSeconds'].every((key) => item.estimate[key] === null ||
          (Number.isSafeInteger(item.estimate[key]) && item.estimate[key] >= 0)) ||
        !Array.isArray(item.estimate.basis) || !item.estimate.basis.every((value) => typeof value === 'string')) {
      throw new Error('An assessment differs from the selected route or observation generation.');
    }
  }
}

function renderComparison(result, selections) {
  const cards = [];
  result.assessments.forEach((item, index) => {
    const selection = selections[index];
    const card = document.createElement('article');
    card.className = `assessment-card assessment-${item.status.toLowerCase()}`;
    const title = document.createElement('h3');
    title.textContent = `${selection.displayName} · ${selection.environmentId}`;
    const status = document.createElement('p');
    status.className = 'assessment-status';
    status.textContent = `${item.status} · assessment only`;
    const observation = document.createElement('p');
    observation.textContent = `Generation ${selection.generation} · ${item.destination.platformFamily} · Route maturity: ${item.routeMaturity}`;
    const currency = document.createElement('p');
    currency.className = 'muted';
    currency.textContent = [[result.sourceInput, 'Source'], [result.destinationInputs[index], 'Destination']]
      .map(([input, side]) => `${side}: pinned generation ${input.generation}; latest observed generation ` +
        `${input.latestObservation.generation} (${input.latestObservation.collectionCompleteness})` +
        (input.superseded ? '. Historical pin; current eligibility unknown.' : '.'))
      .join(' ');
    const issues = document.createElement('ul');
    issues.className = 'assessment-issues';
    for (const issue of item.issues) {
      const entry = document.createElement('li');
      const label = document.createElement('strong');
      label.textContent = `${issue.severity} · ${issue.code}`;
      const reason = document.createElement('p');
      reason.textContent = issue.reason;
      const remediation = document.createElement('p');
      remediation.textContent = `Next: ${issue.remediation}`;
      entry.append(label, reason, remediation);
      issues.append(entry);
    }
    const estimate = document.createElement('p');
    estimate.className = 'muted';
    estimate.textContent = `Copy phase estimate: ${item.estimate.copyPhaseSeconds === null ? 'Unknown' : item.estimate.copyPhaseSeconds + ' seconds'}. ` +
      `Transfer size: ${item.estimate.transferBytes === null ? 'Unknown' : item.estimate.transferBytes + ' bytes'}. ` +
      `Confidence: ${item.estimate.confidence}. This is not an outage estimate.`;
    const basis = document.createElement('p');
    basis.className = 'muted';
    basis.textContent = item.estimate.basis.join(' · ');
    card.append(title, status, observation, currency, issues, estimate, basis);
    cards.push(card);
  });
  $('comparison-results').replaceChildren(...cards);
  $('comparison-results').hidden = false;
  $('comparison-status').textContent = `Assessed ${displayTime(result.assessedAt)} against the selected generations. Execution is not authorized.`;
}

async function compareDestinations() {
  invalidateComparison('Comparing the selected observations…');
  let body;
  try { body = comparisonBody(); } catch (error) {
    $('comparison-status').textContent = error.message;
    return;
  }
  const selections = comparisonDestinations.map((item) => ({ ...item }));
  const requestNumber = ++comparisonRequest;
  const version = tokenVersion;
  comparisonBusy = true;
  updateComparisonControls();
  try {
    const result = await requestComparison(body);
    if (requestNumber !== comparisonRequest || version !== tokenVersion || !accessToken) return;
    validateComparison(result, body);
    renderComparison(result, selections);
  } catch (error) {
    if (requestNumber === comparisonRequest && version === tokenVersion && accessToken) {
      $('comparison-status').textContent = error.message || 'The assessment request could not be completed.';
    }
  } finally {
    if (requestNumber === comparisonRequest && version === tokenVersion) {
      comparisonBusy = false;
      updateComparisonControls();
    }
  }
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
$('environment-form').addEventListener('submit', (event) => {
  event.preventDefault();
  loadEnvironments(true);
});
$('environment-selector').addEventListener('change', (event) => {
  if (event.target.value) $('environment-wsd').value = event.target.value;
});
$('more-environments').addEventListener('click', () => loadEnvironments());
$('discovery-environment').addEventListener('change', () => clearDiscovery());
$('discovery-form').addEventListener('submit', (event) => {
  event.preventDefault();
  loadDiscovery();
});
$('more-discovery').addEventListener('click', () => loadObservedObjects());
$('comparison-workload').addEventListener('change', () => invalidateComparison());
$('destination-form').addEventListener('submit', (event) => {
  event.preventDefault();
  loadDestinationEnvironments(true);
});
$('destination-wsd').addEventListener('change', () => {
  destinationRequest++;
  destinationAddRequest++;
  destinationOptions = new Map();
  $('destination-environment').replaceChildren(new Option('Choose an environment', ''));
  $('destination-environment').disabled = true;
  $('more-destinations').hidden = true;
  invalidateComparison();
});
$('destination-environment').addEventListener('change', () => {
  destinationAddRequest++;
  invalidateComparison();
});
$('add-destination').addEventListener('click', () => addDestination());
$('more-destinations').addEventListener('click', () => loadDestinationEnvironments());
for (const id of ['comparison-method', 'comparison-guest', 'comparison-network', 'comparison-data']) {
  $(id).addEventListener(id === 'comparison-method' ? 'change' : 'input', () => invalidateComparison());
}
$('comparison-form').addEventListener('submit', (event) => {
  event.preventDefault();
  compareDestinations();
});
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

// The draft component uses the same tab identity, not a separate login or store.
try {
  applicationDraftWorkspace = ApplicationDraftWorkspace.mount({
    document, window, session: () => ({token: accessToken, version: tokenVersion}),
    fetch: (...args) => fetch(...args),
    rejectSession: () => clearSession('Token rejected. An attempted draft save may still require history reconciliation.')
  });
} catch (_) {
  $('draft-status').textContent = 'Application draft workspace unavailable. Use the supported operator CLI.';
}

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
