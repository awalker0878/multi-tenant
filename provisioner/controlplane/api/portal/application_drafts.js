'use strict';

// An API client for existing UNREVIEWED drafts, never an owner-review authority.
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
  const validId = (v) => typeof v === 'string' && ID.test(v);
  const integer = (v, min = 1) => Number.isSafeInteger(v) && v >= min;
  const plain = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
  const keys = (v, names) => plain(v) && Object.keys(v).length === names.length &&
    names.every((name) => Object.hasOwn(v, name));
  const copy = (v) => JSON.parse(JSON.stringify(v));
  const canonical = (v) => JSON.stringify(v, function (_, item) {
    return plain(item) ? Object.fromEntries(Object.keys(item).sort().map((key) => [key, item[key]])) : item;
  });
  const scopeValid = (v) => keys(v, SCOPE) && SCOPE.every((key) => validId(v[key])) &&
    ['vmware', 'nutanix', 'openstack'].includes(v.platform_family);
  const text = (v, max = 256) => typeof v === 'string' && v.length > 0 &&
    v.length <= max && v === v.trim() && !/[\u0000-\u001f\u007f]/.test(v);

  function strictJson(source) {
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
    if (typeof source !== 'string' || source.length > MAX_RESPONSE) fail();
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
        record.latestGeneration < record.generation || !SHA.test(record.resultDigest) ||
        !SHA.test(record.proposalDigest) || !SHA.test(record.recordDigest) ||
        !text(record.recordedBy, 512) || !text(record.recordedAt, 64) ||
        !Number.isFinite(Date.parse(record.recordedAt)) || record.status !== 'UNREVIEWED' ||
        record.ownershipAccepted !== false || record.executionAuthorized !== false ||
        record.sourceSuperseded !== (record.generation !== record.latestGeneration) ||
        !keys(proposal, ['format', 'discoveryDigest', 'scope', 'draft', 'dependencies']) ||
        proposal.format !== 'hosting-application-group-candidate/1' ||
        proposal.discoveryDigest !== record.resultDigest || canonical(proposal.scope) !== canonical(record.scope) ||
        !keys(draft, ['applicationGroupId', 'name', 'ownerId', 'members', 'datasetIds', 'consistencyGroups', 'startupOrder']) ||
        draft.applicationGroupId !== groupId || !text(draft.name) || !validId(draft.ownerId) ||
        !Array.isArray(draft.members) || draft.members.length < 2 || draft.members.length > 100 ||
        !Array.isArray(draft.datasetIds) || !draft.datasetIds.length || draft.datasetIds.length > 1000 ||
        !draft.datasetIds.every(validId) || new Set(draft.datasetIds).size !== draft.datasetIds.length ||
        !Array.isArray(draft.consistencyGroups) || !draft.consistencyGroups.length || draft.consistencyGroups.length > 100 ||
        !Array.isArray(proposal.dependencies) || proposal.dependencies.length > 500) throw new Error('Invalid draft response.');
    const memberIds = new Set(), nativeIds = new Set(), groups = new Set(), datasets = [];
    for (const member of draft.members) {
      if (!keys(member, ['workloadId', 'nativeVm']) || !validId(member.workloadId) ||
          memberIds.has(member.workloadId) || !Array.isArray(member.nativeVm) || member.nativeVm.length !== 5 ||
          canonical(member.nativeVm.slice(0, 4)) !== canonical([record.scope.endpoint_id,
            record.scope.native_scope_id, record.scope.platform_family, 'vm']) ||
          !text(member.nativeVm[4], 512) || nativeIds.has(member.nativeVm[4])) throw new Error('Invalid member binding.');
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
    const assertionIds = new Set();
    for (const edge of proposal.dependencies) {
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
    validateOrder(draft.startupOrder, draft.members, proposal.dependencies);
    return copy(record);
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

  function editedRequest(record, name, owner, orderText) {
    if (record.sourceSuperseded) throw new Error('The source generation is superseded.');
    if (!text(name) || !validId(owner)) throw new Error('Enter a valid name and proposed owner ID.');
    const body = {generation: record.generation, resultDigest: record.resultDigest,
      expectedRevision: record.revision, ...copy({draft: record.proposal.draft, dependencies: record.proposal.dependencies})};
    const order = orderText.trim().split(/\s+/);
    validateOrder(order, body.draft.members, body.dependencies);
    body.draft.name = name; body.draft.ownerId = owner; body.draft.startupOrder = order;
    if (new TextEncoder().encode(JSON.stringify(body)).length > MAX_REQUEST) throw new Error('Proposal exceeds the request limit.');
    return body;
  }

  function mount({document, session, fetch, window, rejectSession = () => {}, timeoutMs = 15000}) {
    const $ = (id) => document.getElementById('draft-' + id);
    let epoch = 0, busy = false, loaded = null, historical = false, dirty = false;
    let unknown = null, cursor = null, selectedEnvironment = null, pageScope = null, controller = null;
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
      for (const id of ['name', 'owner', 'order']) $(id).disabled = busy || !loaded || historical || loaded.sourceSuperseded || !!unknown;
      const canSave = !busy && loaded && !historical && !loaded.sourceSuperseded && dirty && !unknown;
      $('save').disabled = !canSave || !$('confirm').checked;
      $('discard').disabled = busy || !loaded && !unknown;
      $('confirm').disabled = !canSave;
      $('reconcile').hidden = !unknown;
      $('reconcile').disabled = busy;
    }
    function clear() {
      epoch++; controller?.abort(); controller = null;
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
        if (result.status !== 200 || !keys(page, ['format', 'environmentId', 'scope', 'latestGeneration', 'consistency', 'items', 'nextAfter', 'executionAuthorized']) || page.format !== 'hosting-application-draft-list/1' ||
            page.environmentId !== env || !scopeValid(page.scope) || pageScope && canonical(page.scope) !== canonical(pageScope) ||
            page.consistency !== 'LIVE_PAGE' || page.executionAuthorized !== false ||
            !(page.latestGeneration === null || integer(page.latestGeneration)) ||
            !Array.isArray(page.items) || page.items.length > 50 ||
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
              !SHA.test(item.resultDigest) || !SHA.test(item.proposalDigest) || !SHA.test(item.recordDigest) ||
              Object.hasOwn(item, 'proposal') || !integer(page.latestGeneration) || item.generation > page.latestGeneration ||
              item.sourceSuperseded !== (item.generation !== page.latestGeneration)) throw new Error('Invalid draft summary.');
          previous = item.applicationGroupId;
        }
        if (page.nextAfter !== null && (!page.items.length || page.nextAfter !== previous || page.nextAfter === after)) throw new Error('Invalid continuation.');
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
      loaded = record; dirty = false; $('confirm').checked = false; $('editor').hidden = false;
      $('name').value = record.proposal.draft.name; $('owner').value = record.proposal.draft.ownerId;
      $('order').value = record.proposal.draft.startupOrder.join('\n');
      $('binding').textContent = `${record.environmentId} · ${record.applicationGroupId} · revision ${record.revision} · generation ${record.generation}\nResult: ${record.resultDigest}\nRecorded by ${record.recordedBy} at ${record.recordedAt}\n${record.sourceSuperseded ? 'SUPERSEDED SOURCE — read only.' : historical ? 'HISTORICAL REVISION — read only.' : 'UNREVIEWED — editing preserves this source pin.'}`;
      for (const id of ['members', 'datasets', 'dependencies']) $(id).replaceChildren();
      for (const member of record.proposal.draft.members) {
        const row = document.createElement('tr'); cell(row, member.workloadId); cell(row, member.nativeVm.join(' / ')); $('members').append(row);
      }
      for (const group of record.proposal.draft.consistencyGroups) {
        const row = document.createElement('tr'); cell(row, group.groupId); cell(row, group.datasetIds.join(', ')); $('datasets').append(row);
      }
      for (const edge of record.proposal.dependencies) {
        const row = document.createElement('tr');
        for (const field of ['assertionId', 'sourceWorkloadId', 'relation', 'targetWorkloadId', 'state', 'unknownReason', 'source', 'sourceReference', 'observedAt']) cell(row, edge[field]);
        $('dependencies').append(row);
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
        status('Draft loaded. Membership, datasets and dependency evidence are retained read-only; no approval is issued.');
      } catch (_) { if (same(who, version)) status('Draft unavailable or inconsistent. No editable draft was loaded.'); }
      finally { if (same(who, version)) { busy = false; controls(); } }
    }
    async function save() {
      if (busy || !dirty || !loaded || historical || loaded.sourceSuperseded || unknown || !$('confirm').checked) return;
      let who, body;
      try { who = identity(); body = editedRequest(loaded, $('name').value, $('owner').value, $('order').value); }
      catch (error) { status(error.message); return; }
      const original = copy(loaded), version = ++epoch;
      busy = true; controls();
      unknown = {environmentId: original.environmentId, applicationGroupId: original.applicationGroupId,
        revision: original.revision + 1, body: copy(body), scope: copy(original.scope)};
      status('Saving an unreviewed revision. A lost acknowledgement requires reconciliation, not an automatic retry.');
      try {
        const result = await request(pathFor(original.environmentId, original.applicationGroupId), 'PUT', body, who, version);
        if (!same(who, version)) return;
        if (result.status === 409 && result.value?.error?.code === 'APPLICATION_DRAFT_CONFLICT') {
          unknown = null; historical = true; dirty = false;
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
    $('list').addEventListener('click', () => list()); $('next').addEventListener('click', () => list(true));
    $('confirm').addEventListener('change', controls);
    $('load').addEventListener('click', load); $('reconcile').addEventListener('click', reconcile);
    $('form').addEventListener('submit', (event) => { event.preventDefault(); return save(); });
    for (const id of ['name', 'owner', 'order']) $(id).addEventListener('input', () => { if (!busy && loaded && !historical && !unknown) { dirty = true; $('confirm').checked = false; status('Unsaved local changes; source, membership and dependency evidence remain pinned.'); controls(); } });
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
    return {clear, list, load, save, reconcile};
  }
  return {mount, strictJson, validateRecord, editedRequest, canonical};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = ApplicationDraftWorkspace;
