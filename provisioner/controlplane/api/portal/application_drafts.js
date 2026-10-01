'use strict';

// An API client for creating and editing UNREVIEWED drafts, never an owner-review authority.
const ApplicationDraftWorkspace = (() => {
  const ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
  const SHA = /^[0-9a-f]{64}$/;
  const SCOPE = ['organization_id', 'tenant_id', 'site_id', 'security_domain_id',
    'endpoint_id', 'native_scope_id', 'platform_family'];
  const MAX_REQUEST = 131072, MAX_RESPONSE = 524288;
  const RECORD = ['format', 'environmentId', 'scope', 'applicationGroupId', 'revision',
    'generation', 'resultDigest', 'proposalDigest', 'recordedBy', 'recordedAt', 'recordDigest',
    'proposal', 'status', 'latestGeneration', 'sourceSuperseded', 'ownershipAccepted', 'executionAuthorized'];
  const SUMMARY = RECORD.filter((key) => key !== 'proposal').concat(
    ['name', 'ownerId', 'memberCount', 'datasetCount', 'dependencyCount', 'unknownDependencyCount']);
  const validSha = (v) => typeof v === 'string' && SHA.test(v);
  const validId = (v) => typeof v === 'string' && ID.test(v);
  const integer = (v, min = 1) => Number.isSafeInteger(v) && v >= min;
  const plain = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
  const keys = (v, names) => plain(v) && Object.keys(v).length === names.length &&
    names.every((name) => Object.hasOwn(v, name));
  const copy = (v) => JSON.parse(JSON.stringify(v));
  const canonical = (v) => JSON.stringify(v, function (_, item) {
    return plain(item) ? Object.fromEntries(Object.keys(item).sort().map((key) => [key, item[key]])) : item;
  });
  const nativeText = (v) => typeof v === 'string' && v.length <= 512 && v.trim().length > 0 &&
    !/[\u0000-\u001f\u007f]/.test(v);
  const scopeValid = (v) => keys(v, SCOPE) && SCOPE.filter((key) => key !== 'native_scope_id').every((key) => validId(v[key])) &&
    nativeText(v.native_scope_id) && ['vmware', 'nutanix', 'openstack'].includes(v.platform_family);
  const text = (v, max = 256) => typeof v === 'string' && v.length > 0 &&
    v.length <= max && v === v.trim() && !/[\u0000-\u001f\u007f]/.test(v);

  function strictJson(source, maximum = MAX_RESPONSE) {
    // JSON.parse alone loses duplicate keys and rounds large integer identities.
    let position = 0;
    const fail = () => { throw new Error('Invalid bounded API JSON.'); };
    const space = () => { while (/[\t\n\r ]/.test(source[position] ?? '') && position < source.length) position++; };
    function string() {
      const match = /^"(?:[^"\\\u0000-\u001f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"/.exec(source.slice(position));
      if (!match) fail();
      position += match[0].length;
      return JSON.parse(match[0]);
    }
    function value(depth = 0) {
      space();
      if (depth > 24) fail();
      const start = source[position];
      if (start === '"') return string();
      if (start === '{' || start === '[') {
        position++;
        const object = start === '{', end = object ? '}' : ']';
        const result = object ? Object.create(null) : [], seen = new Set();
        space();
        if (source[position] === end) { position++; return result; }
        let count = 0;
        while (position < source.length) {
          if (++count > 5000) fail();
          space();
          let key;
          if (object) {
            key = string();
            if (seen.has(key)) fail();
            seen.add(key); space();
            if (source[position++] !== ':') fail();
          }
          const item = value(depth + 1);
          if (object) result[key] = item; else result.push(item);
          space();
          const next = source[position++];
          if (next === end) return result;
          if (next !== ',') fail();
        }
        fail();
      }
      const token = /^(?:true|false|null|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)/.exec(source.slice(position));
      if (!token) fail();
      position += token[0].length;
      const parsed = JSON.parse(token[0]);
      if (typeof parsed === 'number' && (!Number.isFinite(parsed) ||
          Number.isInteger(parsed) && !Number.isSafeInteger(parsed) || /[.eE]/.test(token[0]))) fail();
      return parsed;
    }
    if (!integer(maximum) || maximum > 1048576 || typeof source !== 'string' ||
        source.length > maximum || new TextEncoder().encode(source).length > maximum) fail();
    const result = value(); space();
    if (position !== source.length) fail();
    return result;
  }

  function validateRecord(record, environmentId, groupId, revision = null, scope = null) {
    const proposal = record?.proposal, draft = proposal?.draft;
    if (!keys(record, RECORD) || record.format !== 'hosting-application-draft-revision/1' ||
        record.environmentId !== environmentId || record.applicationGroupId !== groupId ||
        !scopeValid(record.scope) || scope && canonical(record.scope) !== canonical(scope) ||
        !integer(record.revision) || revision !== null && record.revision !== revision ||
        !integer(record.generation) || !integer(record.latestGeneration) ||
        record.latestGeneration < record.generation || !validSha(record.resultDigest) ||
        !validSha(record.proposalDigest) || !validSha(record.recordDigest) ||
        !text(record.recordedBy, 512) || !text(record.recordedAt, 64) ||
        !Number.isFinite(Date.parse(record.recordedAt)) || record.status !== 'UNREVIEWED' ||
        record.ownershipAccepted !== false || record.executionAuthorized !== false ||
        record.sourceSuperseded !== (record.generation !== record.latestGeneration) ||
        !keys(proposal, ['format', 'discoveryDigest', 'scope', 'draft', 'dependencies']) ||
        proposal.format !== 'hosting-application-group-candidate/1' ||
        proposal.discoveryDigest !== record.resultDigest || canonical(proposal.scope) !== canonical(record.scope)) throw new Error('Invalid draft response.');
    validateProposal(draft, proposal.dependencies, record.scope, groupId);
    return copy(record);
  }

  function validateProposal(draft, dependencies, scope, groupId) {
    if (!scopeValid(scope) || !validId(groupId) || !keys(draft, ['applicationGroupId', 'name', 'ownerId', 'members', 'datasetIds', 'consistencyGroups', 'startupOrder']) ||
        draft.applicationGroupId !== groupId || !text(draft.name) || !validId(draft.ownerId) ||
        !Array.isArray(draft.members) || draft.members.length < 2 || draft.members.length > 100 ||
        !Array.isArray(draft.datasetIds) || !draft.datasetIds.length || draft.datasetIds.length > 1000 ||
        !draft.datasetIds.every(validId) || new Set(draft.datasetIds).size !== draft.datasetIds.length ||
        !Array.isArray(draft.consistencyGroups) || !draft.consistencyGroups.length || draft.consistencyGroups.length > 100 ||
        !Array.isArray(dependencies) || dependencies.length > 500) throw new Error('Invalid application proposal.');
    const memberIds = new Set(), nativeIds = new Set(), groups = new Set(), datasets = [];
    for (const member of draft.members) {
      if (!keys(member, ['workloadId', 'nativeVm']) || !validId(member.workloadId) ||
          memberIds.has(member.workloadId) || !Array.isArray(member.nativeVm) || member.nativeVm.length !== 5 ||
          canonical(member.nativeVm.slice(0, 4)) !== canonical([scope.endpoint_id,
            scope.native_scope_id, scope.platform_family, 'vm']) ||
          !nativeText(member.nativeVm[4]) || nativeIds.has(member.nativeVm[4])) throw new Error('Invalid member binding.');
      memberIds.add(member.workloadId); nativeIds.add(member.nativeVm[4]);
    }
    for (const group of draft.consistencyGroups) {
      if (!keys(group, ['groupId', 'datasetIds']) || !validId(group.groupId) || groups.has(group.groupId) ||
          !Array.isArray(group.datasetIds) || !group.datasetIds.length || group.datasetIds.length > 1000 ||
          !group.datasetIds.every(validId)) throw new Error('Invalid dataset grouping.');
      groups.add(group.groupId); datasets.push(...group.datasetIds);
    }
    if (new Set(datasets).size !== datasets.length || canonical([...datasets].sort()) !==
        canonical([...draft.datasetIds].sort())) throw new Error('Invalid dataset coverage.');
    validateDependencies(dependencies, memberIds);
    validateOrder(draft.startupOrder, draft.members, dependencies);
    return copy({draft, dependencies});
  }

  function validateDependencies(dependencies, memberIds) {
    if (!Array.isArray(dependencies) || dependencies.length > 500) throw new Error('Dependency assertion limit exceeded.');
    const assertionIds = new Set();
    for (const edge of dependencies) {
      if (!keys(edge, ['assertionId', 'sourceWorkloadId', 'targetWorkloadId', 'relation', 'state',
          'source', 'sourceReference', 'observedAt', 'unknownReason']) || !validId(edge.assertionId) ||
          assertionIds.has(edge.assertionId) || !memberIds.has(edge.sourceWorkloadId) ||
          !['STARTS_AFTER', 'SERVICE_CALL'].includes(edge.relation) ||
          !['CMDB', 'GUEST', 'MONITORING', 'APPLICATION_OWNER'].includes(edge.source) ||
          !validId(edge.sourceReference) || !text(edge.observedAt, 64) ||
          !Number.isFinite(Date.parse(edge.observedAt)) ||
          !(edge.state === 'KNOWN' && memberIds.has(edge.targetWorkloadId) &&
            edge.targetWorkloadId !== edge.sourceWorkloadId && edge.unknownReason === null ||
            edge.state === 'UNKNOWN' && edge.targetWorkloadId === null &&
            ['UNRESOLVED_TARGET', 'NOT_OBSERVED', 'CONFLICTING_SOURCES', 'EXTERNAL_DEPENDENCY'].includes(edge.unknownReason))) {
        throw new Error('Invalid dependency assertion.');
      }
      assertionIds.add(edge.assertionId);
    }
  }

  function validateOrder(order, members, dependencies) {
    const ids = members.map((member) => member.workloadId);
    if (!Array.isArray(order) || !order.every(validId) || order.length !== ids.length ||
        new Set(order).size !== order.length || order.some((id) => !ids.includes(id)) ||
        dependencies.some((edge) => edge.state === 'KNOWN' && edge.relation === 'STARTS_AFTER' &&
          order.indexOf(edge.targetWorkloadId) >= order.indexOf(edge.sourceWorkloadId))) {
      throw new Error('Startup order must include every member once and respect known dependencies.');
    }
  }

  function validateList(page, env, after = null, scope = null, limit = 50) {
    if (!keys(page, ['format', 'environmentId', 'scope', 'latestGeneration', 'consistency', 'items', 'nextAfter', 'executionAuthorized']) || page.format !== 'hosting-application-draft-list/1' ||
        page.environmentId !== env || !scopeValid(page.scope) || scope && canonical(page.scope) !== canonical(scope) ||
        page.consistency !== 'LIVE_PAGE' || page.executionAuthorized !== false ||
        !(page.latestGeneration === null || integer(page.latestGeneration)) ||
        !Array.isArray(page.items) || page.items.length > limit ||
        !(page.nextAfter === null || validId(page.nextAfter))) throw new Error('Invalid draft listing.');
    let previous = after;
    for (const item of page.items) {
      if (!keys(item, SUMMARY) || item.format !== 'hosting-application-draft-revision/1' ||
          item.environmentId !== env || canonical(item.scope) !== canonical(page.scope) || item.latestGeneration !== page.latestGeneration ||
          !text(item.recordedBy, 512) || !text(item.recordedAt, 64) || !Number.isFinite(Date.parse(item.recordedAt)) ||
          !integer(item.memberCount, 2) || item.memberCount > 100 || !integer(item.datasetCount) || item.datasetCount > 1000 ||
          !integer(item.dependencyCount, 0) || item.dependencyCount > 500 || !integer(item.unknownDependencyCount, 0) ||
          item.unknownDependencyCount > item.dependencyCount || !validId(item.applicationGroupId) || previous !== null && item.applicationGroupId <= previous ||
          item.status !== 'UNREVIEWED' || item.ownershipAccepted !== false || item.executionAuthorized !== false ||
          !integer(item.revision) || !integer(item.generation) || !text(item.name) || !validId(item.ownerId) ||
          !validSha(item.resultDigest) || !validSha(item.proposalDigest) || !validSha(item.recordDigest) ||
          Object.hasOwn(item, 'proposal') || !integer(page.latestGeneration) || item.generation > page.latestGeneration ||
          item.sourceSuperseded !== (item.generation !== page.latestGeneration)) throw new Error('Invalid draft summary.');
      previous = item.applicationGroupId;
    }
    if (page.nextAfter !== null && (page.items.length !== limit || page.nextAfter !== previous || page.nextAfter === after)) throw new Error('Invalid continuation.');
    return copy(page);
  }

  function editedRequest(record, name, owner, orderText) {
    if (typeof orderText !== 'string' || orderText.length > 12900) throw new Error('Invalid startup order input.');
    const draft = {...copy(record.proposal.draft), name, ownerId: owner,
      startupOrder: orderText.trim().split(/\s+/)};
    return proposalRequest(record, draft, record.proposal.dependencies, record.revision);
  }

  const KINDS = ['vm', 'disk', 'nic', 'volume', 'image', 'network', 'pool', 'cluster', 'host', 'datastore', 'quota'];
  const MAX_PAGES = 200;

  function utcInput(value) {
    const match = typeof value === 'string' && /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?(?:Z|\+00:00)$/.exec(value);
    if (!match || Number(value.slice(0, 4)) < 1) throw new Error('Enter a UTC timestamp including seconds and Z or +00:00.');
    const date = new Date(match[1] + 'Z');
    if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 19) !== match[1]) throw new Error('Invalid UTC calendar time.');
    const fraction = (match[2] || '').padEnd(6, '0');
    return match[1] + (fraction === '000000' ? '' : '.' + fraction) + '+00:00';
  }

  function validateGeneration(page, env, generation) {
    if (!keys(page, ['environmentId', 'generation', 'campaignId', 'resultDigest', 'capturedAt',
        'completeness', 'objectCount', 'collectionErrorCount', 'missingPrivilegeCount']) ||
        page.environmentId !== env || page.generation !== generation || !integer(page.generation) ||
        !validId(page.campaignId) || !validSha(page.resultDigest) ||
        !['COMPLETE', 'PARTIAL', 'UNKNOWN'].includes(page.completeness) ||
        !['objectCount', 'collectionErrorCount', 'missingPrivilegeCount'].every((key) => integer(page[key], 0)) ||
        page.completeness === 'COMPLETE' && (page.collectionErrorCount || page.missingPrivilegeCount)) {
      throw new Error('Source observation changed or is invalid.');
    }
    utcInput(page.capturedAt);
    return copy(page);
  }

  function objectCursor(item) {
    // This is the control API's identity cursor, not a native API URL or cursor.
    const bytes = new TextEncoder().encode(JSON.stringify([item.resourceKind, item.nativeId]));
    return btoa(String.fromCharCode(...bytes)).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '');
  }

  function validateObjectPage(page, source, seen, after, count) {
    if (!keys(page, ['environmentId', 'generation', 'items', 'nextAfter']) ||
        page.environmentId !== source.environmentId || page.generation !== source.generation ||
        !Array.isArray(page.items) || page.items.length > 50 ||
        count + page.items.length > source.objectCount) throw new Error('Observation page changed.');
    const pageKeys = new Set();
    for (const item of page.items) {
      const key = canonical([item?.resourceKind, item?.nativeId]);
      if (!keys(item, ['resourceKind', 'nativeId', 'displayName', 'unknownCount', 'objectDigest']) ||
          !KINDS.includes(item.resourceKind) || !nativeText(item.nativeId) ||
          !(item.displayName === null || typeof item.displayName === 'string' && item.displayName.length <= 256 &&
            !/[\u0000-\u001f\u007f]/.test(item.displayName)) ||
          !integer(item.unknownCount, 0) || !validSha(item.objectDigest) || seen.has(key) || pageKeys.has(key)) {
        throw new Error('Invalid or repeated observation identity.');
      }
      pageKeys.add(key);
    }
    if (page.nextAfter !== null && (page.items.length !== 50 ||
        page.nextAfter !== objectCursor(page.items.at(-1)) || page.nextAfter === after ||
        count + page.items.length >= source.objectCount)) throw new Error('Invalid identity continuation.');
    if (page.nextAfter === null && count + page.items.length !== source.objectCount) throw new Error('Stored object count differs.');
    return copy(page);
  }

  function proposalRequest(source, draft, dependencies, expectedRevision) {
    // Initial and subsequent authoring use one request contract, with no inferred revision.
    if (!source || !validId(source.environmentId) || !scopeValid(source.scope) || !integer(source.generation) ||
        !validSha(source.resultDigest) || source.sourceSuperseded || !integer(expectedRevision, 0) ||
        expectedRevision >= Number.MAX_SAFE_INTEGER) throw new Error('An exact source and writable revision are required.');
    const content = validateProposal(draft, dependencies, source.scope, draft?.applicationGroupId);
    const body = {generation: source.generation, resultDigest: source.resultDigest, expectedRevision, ...content};
    if (new TextEncoder().encode(JSON.stringify(body)).length > MAX_REQUEST) throw new Error('Proposal exceeds the request limit.');
    return body;
  }

  function mount({document, session, fetch, window, rejectSession = () => {}, timeoutMs = 15000, onSelection = () => {}}) {
    const $ = (id) => document.getElementById('draft-' + id);
    let epoch = 0, busy = false, loaded = null, historical = false, dirty = false;
    let unknown = null, cursor = null, selectedEnvironment = null, pageScope = null, controller = null;
    let lastSelection = null;
    let authoring = null, members = [], datasets = [], groups = [], dependencies = [];
    let objectAfter = null, objectDone = false, objectCount = 0, objectPages = 0, objectHeld = false;
    let seenObjects = new Set(), visibleObjects = [], memberInputs = [], rowControls = [];
    const authoringFields = ['data-group', 'data-ids', 'edge-id', 'edge-from', 'edge-to', 'edge-relation',
      'edge-state', 'edge-reason', 'edge-source', 'edge-reference', 'edge-time'];
    const selection = () => loaded && !authoring && !objectHeld && !busy && !historical && !dirty && !unknown &&
      !loaded.sourceSuperseded ? copy(loaded) : null;
    const status = (message) => { $('status').textContent = message; };
    const identity = () => {
      const value = session();
      if (!value?.token || !Number.isSafeInteger(value.version)) throw new Error('Sign in first.');
      return value;
    };
    const same = (who, version) => version === epoch && session()?.version === who.version && session()?.token === who.token;
    function controls() {
      for (const id of ['environment', 'group', 'revision', 'list', 'load', 'next']) $(id).disabled = busy || dirty || !!unknown;
      $('next').hidden = cursor === null;
      for (const id of ['name', 'owner', 'order']) $(id).disabled = busy || !(loaded || authoring) || historical || !!loaded?.sourceSuperseded || objectHeld || !!unknown;
      const canSave = !busy && !objectHeld && (loaded || authoring) && !historical && !loaded?.sourceSuperseded && dirty && !unknown;
      $('save').disabled = !canSave || !$('confirm').checked;
      $('discard').disabled = busy || !(loaded || authoring || unknown);
      $('start').disabled = busy || dirty || !!unknown || !session()?.token;
      $('edit-evidence').disabled = busy || !loaded || historical || !!loaded?.sourceSuperseded || dirty || !!unknown || objectHeld;
      $('authoring').hidden = !authoring;
      const locked = busy || !authoring || !!unknown || objectHeld;
      for (const id of [...authoringFields, 'add-group', 'add-edge']) $(id).disabled = locked;
      for (const item of rowControls) item.disabled = locked;
      $('objects').disabled = locked || objectDone || objectPages >= MAX_PAGES;
      $('objects').textContent = objectPages ? 'Next observed identity page' : 'Load observed identities';
      $('confirm').disabled = !canSave;
      $('reconcile').hidden = !unknown;
      $('reconcile').disabled = busy;
      const selected = selection(), fingerprint = selected ? canonical(selected) : null;
      if (fingerprint !== lastSelection) { lastSelection = fingerprint; onSelection(selected); }
    }
    function resetAuthoring() {
      authoring = null; members = []; datasets = []; groups = []; dependencies = [];
      objectAfter = null; objectDone = objectHeld = false; objectCount = objectPages = 0;
      seenObjects = new Set(); visibleObjects = []; memberInputs = []; rowControls = [];
      $('observations').replaceChildren(); $('observation-status').textContent = '';
      for (const id of authoringFields) $(id).value = '';
    }
    function clear() {
      epoch++; controller?.abort(); controller = null;
      resetAuthoring();
      busy = dirty = historical = false; loaded = unknown = cursor = selectedEnvironment = pageScope = null;
      for (const id of ['rows', 'members', 'datasets', 'dependencies', 'binding']) $(id).replaceChildren();
      for (const id of ['environment', 'group', 'revision', 'name', 'owner', 'order']) $(id).value = '';
      $('editor').hidden = true; $('confirm').checked = false; $('confirm-discard').checked = false;
      status('Sign in, then enter an authorized environment to inspect application drafts.'); controls();
    }
    function cell(row, value) {
      const node = document.createElement('td'); node.textContent = String(value ?? 'Unknown'); row.append(node);
    }
    async function request(path, method, body, who, version) {
      if (!same(who, version)) throw new Error('Identity changed.');
      controller = new AbortController();
      const abort = controller, timer = setTimeout(() => abort.abort(), timeoutMs);
      let reader, response;
      try {
        response = await fetch(path, {method, mode: 'same-origin', credentials: 'omit',
          cache: 'no-store', redirect: 'error', referrerPolicy: 'no-referrer', signal: abort.signal,
          headers: {Authorization: `Bearer ${who.token}`, Accept: 'application/json',
            ...(method === 'PUT' ? {'Content-Type': 'application/json'} : {})},
          ...(method === 'PUT' ? {body: JSON.stringify(body)} : {})});
        if (same(who, version) && response.status === 401) { rejectSession(); throw new Error('Identity rejected.'); }
        if (!same(who, version) || response.redirected || !response.body ||
            response.headers.get('content-type')?.split(';')[0].trim().toLowerCase() !== 'application/json') throw new Error('Invalid response.');
        const declared = response.headers.get('content-length');
        if (declared !== null && (!/^[0-9]+$/.test(declared) || Number(declared) > MAX_RESPONSE)) throw new Error('Response exceeds its bound.');
        reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8', {fatal: true});
        let source = '', length = 0;
        while (true) {
          const {done, value} = await reader.read();
          if (!same(who, version) || abort.signal.aborted) throw new Error('Read superseded or timed out.');
          if (done) break;
          length += value.byteLength;
          if (length > MAX_RESPONSE) throw new Error('Response exceeds its bound.');
          source += decoder.decode(value, {stream: true});
        }
        source += decoder.decode();
        // Fetch decodes content codings; Content-Length then measures encoded, not exposed bytes.
        // Both declared and decoded lengths retain their independent finite upper bound.
        const coding = response.headers.get('content-encoding');
        if (declared !== null && (coding === null || coding.trim().toLowerCase() === 'identity') &&
            length !== Number(declared)) throw new Error('Response length differs.');
        if (!same(who, version) || abort.signal.aborted) throw new Error('Read superseded or timed out.');
        return {status: response.status, value: strictJson(source)};
      } finally {
        clearTimeout(timer); abort.abort();
        if (reader) { await reader.cancel().catch(() => {}); reader.releaseLock(); }
        else await response?.body?.cancel().catch(() => {});
        if (controller === abort) controller = null;
      }
    }
    const pathFor = (env, group = null) => `/v1/environments/${encodeURIComponent(env)}/application-drafts` +
      (group === null ? '' : '/' + encodeURIComponent(group));
    function changed() {
      if (!authoring || busy || unknown || objectHeld) return;
      dirty = true; $('confirm').checked = false;
      status('Unsaved proposal. Review the selected tables; original saved revisions are unchanged and assertions are not independently verified.');
      controls();
    }
    function options(id, values) {
      const select = $(id); select.replaceChildren();
      for (const value of ['', ...values]) {
        const option = document.createElement('option'); option.value = value;
        option.textContent = value || 'Choose explicitly'; select.append(option);
      }
      select.value = '';
    }
    function removeButton(row, label, remove) {
      const td = document.createElement('td'), button = document.createElement('button');
      button.type = 'button'; button.textContent = label; rowControls.push(button);
      button.addEventListener('click', () => {
        if (!authoring || busy || unknown || objectHeld) return;
        try { remove(); renderAuthoring(); changed(); } catch (error) { status(error.message); }
      });
      td.append(button); row.append(td);
    }
    function renderAuthoring() {
      const unfinished = new Map(memberInputs.map((input) => [input.nativeId, input.value]));
      rowControls = []; memberInputs = [];
      for (const id of ['members', 'datasets', 'dependencies', 'observations']) $(id).replaceChildren();
      for (const member of members) {
        const row = document.createElement('tr'); cell(row, member.workloadId); cell(row, member.nativeVm.join(' / '));
        removeButton(row, 'Remove member', () => {
          if (dependencies.some((edge) => edge.sourceWorkloadId === member.workloadId || edge.targetWorkloadId === member.workloadId)) {
            throw new Error('Remove dependent assertions explicitly before removing this member.');
          }
          members = members.filter((item) => item !== member);
          $('order').value = $('order').value.trim().split(/\s+/).filter((id) => id !== member.workloadId).join('\n');
        }); $('members').append(row);
      }
      for (const group of groups) {
        const row = document.createElement('tr'); cell(row, group.groupId); cell(row, group.datasetIds.join(', '));
        removeButton(row, 'Remove group', () => {
          groups = groups.filter((item) => item !== group);
          datasets = datasets.filter((id) => !group.datasetIds.includes(id));
        }); $('datasets').append(row);
      }
      for (const edge of dependencies) {
        const row = document.createElement('tr');
        for (const field of ['assertionId', 'sourceWorkloadId', 'relation', 'targetWorkloadId', 'state', 'unknownReason', 'source', 'sourceReference', 'observedAt']) cell(row, edge[field]);
        removeButton(row, 'Remove assertion', () => { dependencies = dependencies.filter((item) => item !== edge); }); $('dependencies').append(row);
      }
      const from = $('edge-from').value, to = $('edge-to').value;
      for (const id of ['edge-from', 'edge-to']) options(id, members.map((member) => member.workloadId));
      if (members.some((member) => member.workloadId === from)) $('edge-from').value = from;
      if (members.some((member) => member.workloadId === to)) $('edge-to').value = to;
      for (const item of visibleObjects.filter((row) => row.resourceKind === 'vm')) {
        const row = document.createElement('tr'); cell(row, item.nativeId); cell(row, item.displayName); cell(row, item.unknownCount);
        if (members.some((member) => member.nativeVm[4] === item.nativeId)) { cell(row, 'Selected'); cell(row, ''); }
        else {
          const td = document.createElement('td'), label = document.createElement('label'), input = document.createElement('input');
          label.textContent = `Proposed workload ID for ${item.nativeId}`;
          input.nativeId = item.nativeId; input.value = unfinished.get(item.nativeId) || '';
          input.maxLength = 128; input.autocomplete = 'off'; input.spellcheck = false;
          input.addEventListener('input', changed); label.append(input); td.append(label); row.append(td);
          rowControls.push(input); memberInputs.push(input);
          removeButton(row, 'Add member', () => {
            if (!validId(input.value) || members.length >= 100 || members.some((member) => member.workloadId === input.value)) {
              throw new Error('Enter a unique logical workload ID; maximum 100 observed members.');
            }
            members.push({workloadId: input.value, nativeVm: [authoring.scope.endpoint_id,
              authoring.scope.native_scope_id, authoring.scope.platform_family, 'vm', item.nativeId]});
            $('order').value = [$('order').value.trim(), input.value].filter(Boolean).join('\n');
          });
        }
        $('observations').append(row);
      }
    }
    function unfinishedRows() {
      return authoringFields.some((id) => $(id).value !== '') || memberInputs.some((input) => input.value !== '');
    }
    async function start() {
      if (busy || dirty || unknown) return;
      let who; try { who = identity(); } catch (_) { status('Sign in first.'); return; }
      const env = $('environment').value.trim(), id = $('group').value.trim();
      if (!validId(env) || !validId(id) || $('revision').value.trim()) { status('Enter an environment and new application ID; leave historical revision empty.'); return; }
      const version = ++epoch; busy = true; loaded = null; historical = false; resetAuthoring(); $('editor').hidden = true; controls();
      status('Reading the authorized draft scope and current stored observation. No draft has been saved.');
      try {
        const listing = await request(pathFor(env) + '?limit=1', 'GET', null, who, version);
        if (!same(who, version)) return;
        if (listing.status !== 200) throw new Error('Scope unavailable');
        const page = validateList(listing.value, env, null, null, 1);
        if (!integer(page.latestGeneration)) throw new Error('No stored observation');
        const response = await request(`/v1/environments/${encodeURIComponent(env)}/discovery/generations/latest`, 'GET', null, who, version);
        if (!same(who, version)) return;
        if (response.status !== 200) throw new Error('Observation unavailable');
        const observation = validateGeneration(response.value, env, page.latestGeneration);
        authoring = {...observation, applicationGroupId: id, scope: copy(page.scope)};
        dirty = true; $('editor').hidden = false;
        for (const field of ['name', 'owner', 'order']) $(field).value = '';
        $('confirm').checked = false;
        $('binding').textContent = `${env} · ${id} · NEW UNSAVED proposal · generation ${authoring.generation}\nResult: ${authoring.resultDigest}\nCaptured: ${authoring.capturedAt} · ${authoring.completeness}\nNo owner review or native authority. Source currency is rechecked by the server at save.`;
        renderAuthoring();
        status('Source pinned. Load identity pages explicitly, select at least two VMs, and propose dataset groups and dependencies.');
      } catch (_) { if (same(who, version)) status('Source unavailable or changed. No new draft was opened; reload explicitly.'); }
      finally { if (same(who, version)) { busy = false; controls(); } }
    }
    async function editEvidence() {
      if (busy || !loaded || dirty || unknown || historical || loaded.sourceSuperseded || objectHeld) return;
      let who; try { who = identity(); } catch (_) { status('Sign in first.'); return; }
      const original = copy(loaded), version = ++epoch;
      busy = true; $('confirm').checked = false; controls();
      status('Checking the saved source pin before opening a new revision proposal. No write is requested.');
      try {
        const response = await request(`/v1/environments/${encodeURIComponent(original.environmentId)}/discovery/generations/latest`, 'GET', null, who, version);
        if (!same(who, version)) return;
        if (response.status !== 200) throw new Error('Source unavailable');
        const observation = validateGeneration(response.value, original.environmentId, original.generation);
        if (observation.resultDigest !== original.resultDigest || original.revision >= Number.MAX_SAFE_INTEGER) throw new Error('Saved source or revision is not writable');
        resetAuthoring();
        authoring = {...observation, applicationGroupId: original.applicationGroupId, scope: copy(original.scope)};
        members = copy(original.proposal.draft.members); datasets = copy(original.proposal.draft.datasetIds);
        groups = copy(original.proposal.draft.consistencyGroups); dependencies = copy(original.proposal.dependencies);
        // Dataset order and original assertion timestamps are copied, not reconstructed.
        dirty = true; renderAuthoring();
        $('binding').textContent += `\nUNSAVED REVISION PROPOSAL — based on revision ${original.revision}; save expects that exact revision.\nCaptured: ${authoring.capturedAt} · ${authoring.completeness}. No rebase or owner-review reuse.`;
        status('Propose membership, dataset and dependency changes. Remove and add replacements explicitly; saving appends a new revision and never overwrites history.');
      } catch (_) {
        if (same(who, version)) {
          objectHeld = true;
          status('Saved source unavailable, changed or not writable. The draft is read only; reload explicitly. No source rebase or write occurred.');
        }
      } finally { if (same(who, version)) { busy = false; controls(); } }
    }
    async function objects() {
      if (busy || !authoring || unknown || objectHeld || objectDone || objectPages >= MAX_PAGES) return;
      if (memberInputs.some((input) => input.value !== '')) { status('Add or clear the unfinished member row before changing pages.'); return; }
      let who; try { who = identity(); } catch (_) { status('Sign in first.'); return; }
      const source = copy(authoring), after = objectAfter, version = ++epoch;
      busy = true; $('confirm').checked = false; controls();
      try {
        const response = await request(`/v1/environments/${encodeURIComponent(source.environmentId)}/discovery/generations/${source.generation}/objects?limit=50` +
          (after === null ? '' : '&after=' + encodeURIComponent(after)), 'GET', null, who, version);
        if (!same(who, version)) return;
        if (response.status !== 200) throw new Error('Observation unavailable');
        const page = validateObjectPage(response.value, source, seenObjects, after, objectCount);
        for (const item of page.items) seenObjects.add(canonical([item.resourceKind, item.nativeId]));
        visibleObjects = page.items; objectCount += page.items.length; objectPages++;
        objectAfter = page.nextAfter; objectDone = objectAfter === null;
        renderAuthoring();
        $('observation-status').textContent = `${objectCount} stored identity summaries inspected; only VMs on this page are selectable. ` +
          (objectDone ? 'Stored page chain ended; native completeness is not established.' : objectPages >= MAX_PAGES ?
            'Browser page budget reached. Selected VMs may still be proposed; remaining estate coverage is not claimed.' : 'Continue only by selecting Next observed identity page.');
      } catch (_) { if (same(who, version)) { objectHeld = true; $('observations').replaceChildren(); status('Observation page unavailable or inconsistent. Discard and reload the source; no authoring save is permitted.'); } }
      finally { if (same(who, version)) { busy = false; controls(); } }
    }
    function addGroup() {
      if (!authoring || busy || unknown || objectHeld) return;
      if ($('data-ids').value.length > 129000) { status('Dataset input exceeds its bounded size.'); return; }
      const groupId = $('data-group').value, datasetIds = $('data-ids').value.trim().split(/\s+/);
      const existing = new Set(groups.flatMap((group) => group.datasetIds));
      if (!validId(groupId) || groups.length >= 100 || groups.some((group) => group.groupId === groupId) ||
          !datasetIds.every(validId) || new Set(datasetIds).size !== datasetIds.length ||
          existing.size + datasetIds.length > 1000 || datasetIds.some((id) => existing.has(id))) {
        status('Enter a unique consistency-group ID and distinct dataset IDs; each dataset must occur in exactly one group.'); return;
      }
      groups.push({groupId, datasetIds}); datasets.push(...datasetIds); $('data-group').value = ''; $('data-ids').value = '';
      renderAuthoring(); changed();
    }
    function addEdge() {
      if (!authoring || busy || unknown || objectHeld) return;
      try {
        const state = $('edge-state').value;
        if (!['KNOWN', 'UNKNOWN'].includes(state) || state === 'UNKNOWN' && $('edge-to').value || state === 'KNOWN' && $('edge-reason').value) {
          throw new Error('Choose known with a target and no unknown reason, or unknown with a reason and no target.');
        }
        const edge = {assertionId: $('edge-id').value, sourceWorkloadId: $('edge-from').value,
          targetWorkloadId: state === 'KNOWN' ? $('edge-to').value : null, relation: $('edge-relation').value,
          state, source: $('edge-source').value, sourceReference: $('edge-reference').value,
          observedAt: utcInput($('edge-time').value), unknownReason: state === 'UNKNOWN' ? $('edge-reason').value : null};
        validateDependencies([...dependencies, edge], new Set(members.map((member) => member.workloadId)));
        validateOrder($('order').value.trim().split(/\s+/), members, [...dependencies, edge]);
        dependencies.push(edge);
        for (const id of authoringFields.filter((id) => id.startsWith('edge-'))) $(id).value = '';
        renderAuthoring(); changed();
      } catch (error) { status(error.message); }
    }
    async function list(next = false) {
      if (busy || dirty || unknown) return;
      let who; try { who = identity(); } catch (_) { status('Sign in first.'); return; }
      const env = $('environment').value.trim(), after = next ? cursor : null, version = ++epoch;
      if (!validId(env) || next && (!after || selectedEnvironment !== env)) { status('Enter a valid environment.'); return; }
      busy = true; controls();
      loaded = null; $('editor').hidden = true; $('rows').replaceChildren();
      if (!next) { cursor = null; pageScope = null; } selectedEnvironment = env;
      status('Loading one live page of unreviewed drafts…');
      try {
        const result = await request(pathFor(env) + '?limit=50' + (after ? '&after=' + encodeURIComponent(after) : ''), 'GET', null, who, version);
        if (!same(who, version)) return;
        const page = result.value;
        if (result.status !== 200) throw new Error('Unavailable');
        validateList(page, env, after, pageScope);
        pageScope = copy(page.scope); cursor = page.nextAfter;
        for (const item of page.items) {
          const row = document.createElement('tr');
          for (const field of ['applicationGroupId', 'name', 'ownerId', 'revision', 'generation']) cell(row, item[field]);
          cell(row, item.sourceSuperseded ? 'Superseded source' : 'Unreviewed'); $('rows').append(row);
        }
        status(`${page.items.length} draft(s) on this live page. Separate pages are not a frozen export.`);
      } catch (_) { if (same(who, version)) { cursor = null; status('Draft listing unavailable or inconsistent. No additional page was fetched.'); } }
      finally { if (same(who, version)) { busy = false; controls(); } }
    }
    function render(record) {
      resetAuthoring();
      loaded = record; dirty = false; $('confirm').checked = false; $('editor').hidden = false;
      $('name').value = record.proposal.draft.name; $('owner').value = record.proposal.draft.ownerId;
      $('order').value = record.proposal.draft.startupOrder.join('\n');
      $('binding').textContent = `${record.environmentId} · ${record.applicationGroupId} · revision ${record.revision} · generation ${record.generation}\nResult: ${record.resultDigest}\nRecorded by ${record.recordedBy} at ${record.recordedAt}\n${record.sourceSuperseded ? 'SUPERSEDED SOURCE — read only.' : historical ? 'HISTORICAL REVISION — read only.' : 'UNREVIEWED — editing preserves this source pin.'}`;
      for (const id of ['members', 'datasets', 'dependencies']) $(id).replaceChildren();
      for (const member of record.proposal.draft.members) {
        const row = document.createElement('tr'); cell(row, member.workloadId); cell(row, member.nativeVm.join(' / ')); cell(row, 'Read only'); $('members').append(row);
      }
      for (const group of record.proposal.draft.consistencyGroups) {
        const row = document.createElement('tr'); cell(row, group.groupId); cell(row, group.datasetIds.join(', ')); cell(row, 'Read only'); $('datasets').append(row);
      }
      for (const edge of record.proposal.dependencies) {
        const row = document.createElement('tr');
        for (const field of ['assertionId', 'sourceWorkloadId', 'relation', 'targetWorkloadId', 'state', 'unknownReason', 'source', 'sourceReference', 'observedAt']) cell(row, edge[field]);
        cell(row, 'Read only'); $('dependencies').append(row);
      }
    }
    async function load() {
      if (busy || dirty || unknown) return;
      let who; try { who = identity(); } catch (_) { status('Sign in first.'); return; }
      const env = $('environment').value.trim(), id = $('group').value.trim(), raw = $('revision').value.trim();
      const revision = raw === '' ? null : Number(raw), version = ++epoch;
      if (!validId(env) || !validId(id) || raw && (!/^[1-9][0-9]*$/.test(raw) || !integer(revision))) { status('Enter valid environment, application and optional revision IDs.'); return; }
      busy = true; loaded = null; historical = revision !== null; $('editor').hidden = true; controls();
      status('Loading the exact draft and its original source…');
      try {
        const result = await request(pathFor(env, id) + (revision === null ? '' : '?revision=' + revision), 'GET', null, who, version);
        if (!same(who, version)) return;
        if (result.status !== 200) throw new Error('Unavailable');
        render(validateRecord(result.value, env, id, revision, selectedEnvironment === env ? pageScope : null));
        status('Draft loaded. Select Edit membership and evidence to propose a new revision; historical and superseded sources remain read only. No approval is issued.');
      } catch (_) { if (same(who, version)) status('Draft unavailable or inconsistent. No editable draft was loaded.'); }
      finally { if (same(who, version)) { busy = false; controls(); } }
    }
    async function save() {
      if (busy || !dirty || !(loaded || authoring) || historical || loaded?.sourceSuperseded || unknown || objectHeld || !$('confirm').checked) return;
      let who, body;
      try {
        who = identity();
        if (authoring && unfinishedRows()) throw new Error('Add or clear unfinished member, dataset and dependency rows before saving.');
        body = authoring ? proposalRequest(authoring, {
          applicationGroupId: authoring.applicationGroupId, name: $('name').value, ownerId: $('owner').value,
          members, datasetIds: datasets, consistencyGroups: groups, startupOrder: $('order').value.trim().split(/\s+/)
        }, dependencies, loaded ? loaded.revision : 0) :
          editedRequest(loaded, $('name').value, $('owner').value, $('order').value);
      }
      catch (error) { status(error.message); return; }
      const original = loaded ? copy(loaded) : {environmentId: authoring.environmentId,
        applicationGroupId: authoring.applicationGroupId, scope: copy(authoring.scope), revision: 0}, version = ++epoch;
      busy = true;
      unknown = {environmentId: original.environmentId, applicationGroupId: original.applicationGroupId,
        revision: original.revision + 1, body: copy(body), scope: copy(original.scope)};
      controls();
      status('Saving an unreviewed revision. A lost acknowledgement requires reconciliation, not an automatic retry.');
      try {
        const result = await request(pathFor(original.environmentId, original.applicationGroupId), 'PUT', body, who, version);
        if (!same(who, version)) return;
        if (result.status === 409 && result.value?.error?.code === 'APPLICATION_DRAFT_CONFLICT') {
          unknown = null; historical = true; dirty = false;
          if (authoring) { resetAuthoring(); $('editor').hidden = true; }
          status('Revision/source conflict. Reload current history before editing; this does not settle an earlier unknown save.'); return;
        }
        if (result.status !== 200) throw new Error('Save acknowledgement unavailable');
        const record = validateRecord(result.value, original.environmentId, original.applicationGroupId, original.revision + 1, original.scope);
        if (record.generation !== body.generation || record.resultDigest !== body.resultDigest ||
            canonical({draft: record.proposal.draft, dependencies: record.proposal.dependencies}) !==
            canonical({draft: body.draft, dependencies: body.dependencies})) throw new Error('Save acknowledgement changed');
        unknown = null; render(record); status('Unreviewed draft saved. Source and all retained assertions match; no ownership or execution was accepted.');
      } catch (_) { if (same(who, version)) status(`SAVE UNKNOWN — reconcile ${original.applicationGroupId} revision ${original.revision + 1} before another save. Cancellation or an error does not prove rollback.`); }
      finally { if (same(who, version)) { busy = false; controls(); } }
    }
    async function reconcile() {
      if (busy || !unknown) return;
      let who; try { who = identity(); } catch (_) { status('Sign in first.'); return; }
      const pending = copy(unknown), version = ++epoch; busy = true; controls();
      try {
        const response = await request(pathFor(pending.environmentId, pending.applicationGroupId) + '?revision=' + pending.revision, 'GET', null, who, version);
        if (!same(who, version)) return;
        if (response.status !== 200) throw new Error('Unresolved');
        const record = validateRecord(response.value, pending.environmentId, pending.applicationGroupId, pending.revision, pending.scope);
        if (record.generation !== pending.body.generation || record.resultDigest !== pending.body.resultDigest ||
            canonical({draft: record.proposal.draft, dependencies: record.proposal.dependencies}) !==
            canonical({draft: pending.body.draft, dependencies: pending.body.dependencies})) throw new Error('Different content');
        // Matching history is visible evidence, not proof this tab authored it.
        historical = true; render(record); unknown = null;
        status('Matching stored revision found. Inspect its recorded author; this is not proof this tab committed it. Reload current before editing.');
      } catch (_) { if (same(who, version)) status('Save remains UNKNOWN. Missing, conflicting or inaccessible history does not prove rollback.'); }
      finally { if (same(who, version)) { busy = false; controls(); } }
    }
    $('edit-evidence').addEventListener('click', editEvidence);
    $('start').addEventListener('click', start); $('objects').addEventListener('click', objects);
    $('add-group').addEventListener('click', addGroup); $('add-edge').addEventListener('click', addEdge);
    for (const id of authoringFields) { $(id).addEventListener('input', changed); $(id).addEventListener('change', changed); }
    $('list').addEventListener('click', () => list()); $('next').addEventListener('click', () => list(true));
    $('confirm').addEventListener('change', controls);
    $('load').addEventListener('click', load); $('reconcile').addEventListener('click', reconcile);
    $('form').addEventListener('submit', (event) => { event.preventDefault(); return save(); });
    for (const id of ['name', 'owner', 'order']) $(id).addEventListener('input', () => { if (!busy && !objectHeld && (loaded || authoring) && !historical && !loaded?.sourceSuperseded && !unknown) { dirty = true; $('confirm').checked = false; status('Unsaved local changes; the original source pin remains unchanged.'); controls(); } });
    $('discard').addEventListener('click', () => {
      if (busy) return;
      if (unknown && !$('confirm-discard').checked) { status('A save is unresolved. Confirm discarding this tab’s reconciliation state first; it does not undo a committed write.'); return; }
      clear();
    });
    for (const id of ['environment', 'group', 'revision']) $(id).addEventListener('input', () => {
      if (busy || dirty || unknown) return;
      epoch++; loaded = null; $('editor').hidden = true;
      if (id === 'environment') { cursor = pageScope = selectedEnvironment = null; $('rows').replaceChildren(); }
      controls();
    });
    window?.addEventListener('pagehide', clear);
    window?.addEventListener('beforeunload', (event) => { if (busy || dirty || unknown) { event.preventDefault(); event.returnValue = ''; } });
    clear();
    return {clear, list, load, start, editEvidence, objects, addGroup, addEdge, save, reconcile, selection};
  }
  return {mount, strictJson, validateRecord, validateProposal, validateList, validateGeneration, validateObjectPage,
    proposalRequest, utcInput, objectCursor, editedRequest, canonical};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = ApplicationDraftWorkspace;
