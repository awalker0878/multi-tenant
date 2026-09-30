'use strict';

// Read-only composition of a retained draft and the existing comparison service.
// Wire consistency is checked here; native evidence and authority stay at the API.
const ApplicationComparisonWorkspace = (() => {
  const ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
  const SHA = /^[0-9a-f]{64}$/;
  const READY = ['REVIEWED_ASSESSMENT_ONLY', 'REVIEWED_WITH_UNKNOWNS'];
  const METHODS = ['REBUILD_RESTORE', 'COLD_VM_CONVERSION', 'SAME_PLATFORM_RELOCATION',
    'APPLICATION_NATIVE', 'WARM_VM_TRANSFER'];
  const FLAGS = ['ownershipAccepted', 'executionAuthorized', 'dependencyEvidenceVerified', 'reservationHeld'];
  const MAX_RESPONSE = 1048576;
  const plain = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
  const keys = (v, names) => plain(v) && Object.keys(v).length === names.length && names.every((k) => Object.hasOwn(v, k));
  const id = (v) => typeof v === 'string' && ID.test(v);
  const sha = (v) => typeof v === 'string' && SHA.test(v);
  const integer = (v, min = 1) => Number.isSafeInteger(v) && v >= min;
  const native = (v) => typeof v === 'string' && v.length > 0 && v.length <= 512 && !!v.trim() && !/[\u0000-\u001f\u007f]/.test(v);
  const copy = (v) => JSON.parse(JSON.stringify(v));
  const canonical = (v) => JSON.stringify(v, (_, item) => plain(item) ?
    Object.fromEntries(Object.keys(item).sort().map((k) => [k, item[k]])) : item)
    .replace(/[\u007f-\uffff]/g, (c) => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0'));
  const equal = (a, b) => canonical(a) === canonical(b);
  const require = (ok) => { if (!ok) throw new Error('Application report differs from the exact selection.'); };
  const statusFor = (issues) => issues.some((i) => i.severity === 'BLOCKER') ? 'BLOCKED' :
    issues.some((i) => i.severity === 'UNKNOWN') ? 'UNKNOWN' :
      issues.some((i) => i.severity === 'CONDITION') ? 'CONDITIONAL' : 'ELIGIBLE';
  function stamp(value) {
    require(typeof value === 'string');
    const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?(?:Z|\+00:00)$/.exec(value);
    require(match && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 19) === match[1]);
    return match[1] + '.' + (match[2] ?? '').padEnd(6, '0');
  }
  async function selectionDigest(body, crypto = globalThis.crypto) {
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(canonical(body)));
    return Array.from(new Uint8Array(digest), (v) => v.toString(16).padStart(2, '0')).join('');
  }
  function buildRequest(record, profiles, selections, settings) {
    require(record && record.status === 'UNREVIEWED' && record.sourceSuperseded === false &&
      record.executionAuthorized === false && record.ownershipAccepted === false &&
      id(record.environmentId) && id(record.applicationGroupId) && integer(record.generation) &&
      integer(record.revision) && sha(record.recordDigest));
    const members = record.proposal?.draft?.members;
    require(Array.isArray(members) && members.length >= 2 && members.length <= 100 &&
      Array.isArray(selections) && selections.length >= 2 && selections.length <= 20 &&
      members.length * selections.length <= 200 && profiles instanceof Map && profiles.size === members.length &&
      METHODS.includes(settings.method) && id(settings.networkMode) && id(settings.dataMode));
    const seen = new Set([record.environmentId]);
    const destinations = selections.map((s) => {
      require(id(s.environmentId) && !seen.has(s.environmentId) && integer(s.generation));
      seen.add(s.environmentId);
      const d = {environmentId: s.environmentId, generation: s.generation};
      if (s.capacityKind || s.capacityNativeId) {
        require(['pool', 'cluster', 'quota', 'datastore'].includes(s.capacityKind) && native(s.capacityNativeId));
        d.capacityKind = s.capacityKind; d.capacityNativeId = s.capacityNativeId;
      }
      return d;
    });
    const memberProfiles = members.map((m) => {
      require(id(m.workloadId) && id(profiles.get(m.workloadId)));
      return {workloadId: m.workloadId, guestProfile: profiles.get(m.workloadId)};
    });
    require(new Set(memberProfiles.map((p) => p.workloadId)).size === members.length);
    const body = {source: {environmentId: record.environmentId, generation: record.generation},
      applicationGroupId: record.applicationGroupId, draftRevision: record.revision,
      draftRecordDigest: record.recordDigest, memberProfiles, destinations,
      method: settings.method, networkMode: settings.networkMode, dataMode: settings.dataMode};
    require(new TextEncoder().encode(canonical(body)).length <= 131072);
    return body;
  }
  function validateReview(v, record) {
    require(keys(v, ['format', 'environmentId', 'scope', 'applicationGroupId', 'draftRevision', 'draftRecordDigest',
      'proposalDigest', 'generation', 'resultDigest', 'latestGeneration', 'latestDraftRevision', 'checkedAt', 'status',
      'ownerDecision', 'ownerId', 'reviewReference', 'evidenceId', 'evidenceRevision', 'evidenceDigest', 'reviewedAt',
      'expiresAt', 'candidateDigest', 'unknownDependencyCount', 'dependencyEvidenceVerified', 'ownershipAccepted', 'executionAuthorized']));
    require(v.format === 'hosting-application-review-status/1' && equal(v.scope, record.scope) &&
      v.environmentId === record.environmentId && v.applicationGroupId === record.applicationGroupId &&
      v.draftRevision === record.revision && v.draftRecordDigest === record.recordDigest &&
      v.proposalDigest === record.proposalDigest && v.generation === record.generation && v.resultDigest === record.resultDigest &&
      integer(v.latestGeneration, v.generation) && integer(v.latestDraftRevision, v.draftRevision) &&
      ['ownershipAccepted', 'executionAuthorized', 'dependencyEvidenceVerified'].every((k) => v[k] === false));
    const checked = stamp(v.checkedAt), ready = READY.includes(v.status);
    const evidence = ['ownerId', 'reviewReference', 'evidenceId', 'evidenceRevision', 'evidenceDigest', 'reviewedAt', 'expiresAt'];
    if (v.ownerDecision === null) require(evidence.every((k) => v[k] === null));
    else {
      require(['ACCEPT_FOR_ASSESSMENT', 'REVOKE'].includes(v.ownerDecision) &&
        ['ownerId', 'reviewReference', 'evidenceId'].every((k) => id(v[k])) && integer(v.evidenceRevision) && sha(v.evidenceDigest));
      require(stamp(v.reviewedAt) <= checked && checked < stamp(v.expiresAt) &&
        Date.parse(v.expiresAt) - Date.parse(v.reviewedAt) <= 3600000);
      require(v.ownerId === record.proposal.draft.ownerId);
    }
    if (ready) {
      const count = record.proposal.dependencies.filter((e) => e.state === 'UNKNOWN').length;
      require(v.ownerDecision === 'ACCEPT_FOR_ASSESSMENT' && sha(v.candidateDigest) && v.unknownDependencyCount === count &&
        (v.status === 'REVIEWED_WITH_UNKNOWNS') === (count > 0));
    } else require(v.candidateDigest === null && v.unknownDependencyCount === null);
    const expected = v.ownerDecision === 'REVOKE' ? ['REVOKED'] : v.latestDraftRevision !== v.draftRevision ?
      ['HELD_SUPERSEDED_DRAFT'] : v.latestGeneration !== v.generation ? ['HELD_SUPERSEDED_INVENTORY'] :
        v.ownerDecision === null ? ['UNREVIEWED'] : [...READY, 'HELD_INCOMPLETE_INVENTORY', 'HELD_STALE_INVENTORY'];
    require(expected.includes(v.status));
    return ready;
  }
  function binding(v, selected) {
    require(keys(v, ['environmentId', 'generation', 'endpointId', 'nativeScopeId', 'platformFamily', 'productTupleId',
      'productTupleDigest', 'observation', 'superseded', 'latestObservation']) &&
      v.environmentId === selected.environmentId && v.generation === selected.generation && integer(v.generation) &&
      id(v.endpointId) && native(v.nativeScopeId) && ['vmware', 'nutanix', 'openstack'].includes(v.platformFamily) &&
      id(v.productTupleId) && sha(v.productTupleDigest) && typeof v.superseded === 'boolean');
    const l = v.latestObservation, o = v.observation;
    require(keys(l, ['generation', 'rawSnapshotDigest', 'capturedAt', 'collectionCompleteness', 'collectionErrors', 'missingPrivileges']) &&
      integer(l.generation, v.generation) && sha(l.rawSnapshotDigest) &&
      ['COMPLETE', 'PARTIAL', 'UNKNOWN'].includes(l.collectionCompleteness) && v.superseded === (l.generation > v.generation));
    stamp(l.capturedAt);
    for (const k of ['collectionErrors', 'missingPrivileges']) require(Array.isArray(l[k]) && l[k].length <= 1024 && l[k].every(native));
    if (o !== null) {
      require(keys(o, ['rawSnapshotDigest', 'assessmentSnapshotDigest', 'normalizerVersion', 'capturedAt',
        'collectionCompleteness', 'assessmentCompleteness']) && sha(o.rawSnapshotDigest) && sha(o.assessmentSnapshotDigest) &&
        o.normalizerVersion === 'hosting-assessment-normalizer/2' &&
        ['COMPLETE', 'PARTIAL', 'UNKNOWN'].includes(o.collectionCompleteness) &&
        ['COMPLETE', 'PARTIAL', 'UNKNOWN'].includes(o.assessmentCompleteness));
      stamp(o.capturedAt);
      if (!v.superseded) require(o.rawSnapshotDigest === l.rawSnapshotDigest && stamp(o.capturedAt) === stamp(l.capturedAt) &&
        o.collectionCompleteness === l.collectionCompleteness);
    }
    return [v.endpointId, v.nativeScopeId, v.platformFamily];
  }
  function issues(v) {
    require(Array.isArray(v) && v.length <= 2048 && v.every((i) => keys(i, ['severity', 'code']) &&
      ['BLOCKER', 'UNKNOWN', 'CONDITION'].includes(i.severity) && id(i.code)));
    return v;
  }
  function validateReport(v, body, digest, record) {
    const common = ['format', 'selectionDigest', 'applicationReview', 'sourceInput', 'destinationInputs',
      'assessments', 'status', 'consistency', ...FLAGS];
    require(v && ['HELD_APPLICATION_REVIEW', 'ASSESSED_NOT_AUTHORIZED'].includes(v.status));
    const held = v.status === 'HELD_APPLICATION_REVIEW';
    require(keys(v, held ? common : [...common, 'startupOrder', 'datasetCount', 'consistencyGroupCount']) &&
      v.format === 'hosting-application-comparison/2' && sha(digest) && v.selectionDigest === digest &&
      v.consistency === 'PINNED_INPUTS_LIVE_RECHECKS' && FLAGS.every((k) => v[k] === false));
    const ready = validateReview(v.applicationReview, record);
    if (held) { require(!ready && v.sourceInput === null && equal(v.destinationInputs, []) && equal(v.assessments, [])); return v; }
    require(ready);
    const scope = binding(v.sourceInput, body.source), draft = record.proposal.draft;
    require(equal(scope, [record.scope.endpoint_id, record.scope.native_scope_id, record.scope.platform_family]) &&
      !v.sourceInput.superseded && v.sourceInput.observation !== null && v.sourceInput.observation.rawSnapshotDigest === record.resultDigest &&
      equal(v.startupOrder, draft.startupOrder) && v.datasetCount === draft.datasetIds.length &&
      v.consistencyGroupCount === draft.consistencyGroups.length && Array.isArray(v.destinationInputs) && Array.isArray(v.assessments) &&
      v.destinationInputs.length === body.destinations.length && v.assessments.length === body.destinations.length);
    const seen = new Set([canonical(scope)]), profiles = new Map(body.memberProfiles.map((m) => [m.workloadId, m.guestProfile]));
    let demands = null;
    body.destinations.forEach((selected, n) => {
      const target = v.destinationInputs[n], nativeScope = binding(target, selected), row = v.assessments[n];
      require(!seen.has(canonical(nativeScope))); seen.add(canonical(nativeScope));
      require(keys(row, ['environmentId', 'status', 'capacity', 'capacityIdentity', 'issues', 'members', 'executionAuthorized']) &&
        row.environmentId === selected.environmentId && row.executionAuthorized === false &&
        equal(row.capacityIdentity, selected.capacityKind ? [...nativeScope, selected.capacityKind, selected.capacityNativeId] : null));
      const all = [...issues(row.issues)], has = (severity, code) => row.issues.some((i) => i.severity === severity && i.code === code);
      require(has('CONDITION', 'APPLICATION_POLICY_DATA_REVIEW_REQUIRED') && has('CONDITION', 'APPLICATION_RESERVATION_NOT_HELD'));
      if (v.applicationReview.unknownDependencyCount > 0) require(has('UNKNOWN', 'APPLICATION_DEPENDENCIES_UNRESOLVED'));
      if (record.proposal.dependencies.some((e) => e.source !== 'APPLICATION_OWNER')) require(has('UNKNOWN', 'APPLICATION_DEPENDENCY_EVIDENCE_UNVERIFIED'));
      require(Array.isArray(row.members) && row.members.length === draft.members.length);
      const names = new Set();
      for (const member of row.members) {
        const original = draft.members.find((m) => m.workloadId === member?.workloadId);
        require(keys(member, ['workloadId', 'nativeVm', 'guestProfile', 'assessedAt', 'status', 'issues', 'executionAuthorized']) &&
          original && !names.has(member.workloadId) && equal(member.nativeVm, original.nativeVm) &&
          member.guestProfile === profiles.get(member.workloadId) && member.executionAuthorized === false &&
          stamp(member.assessedAt) <= stamp(v.applicationReview.checkedAt));
        names.add(member.workloadId); all.push(...issues(member.issues));
        require(member.status === statusFor(member.issues));
        if (target.superseded) require(member.issues.some((i) => i.severity === 'UNKNOWN' && i.code === 'DESTINATION_SNAPSHOT_SUPERSEDED'));
      }
      const c = row.capacity;
      require(keys(c, ['basis', 'memberCount', 'resources', 'reservationHeld', 'transientAndRecoveryFootprintIncluded']) &&
        c.basis === 'SUM_OF_OBSERVED_LOGICAL_VM_REQUIREMENTS' && c.memberCount === draft.members.length &&
        c.reservationHeld === false && c.transientAndRecoveryFootprintIncluded === false &&
        keys(c.resources, ['VM_COUNT', 'VCPU', 'MEMORY', 'STORAGE']));
      const demand = {};
      for (const [resource, q] of Object.entries(c.resources)) {
        require(keys(q, ['required', 'available']) && (q.required === null || integer(q.required)) && (q.available === null || integer(q.available, 0)));
        if (row.capacityIdentity === null || target.observation === null) require(q.available === null);
        if (resource === 'VM_COUNT') require(q.required === draft.members.length);
        if (q.required === null) require(has('UNKNOWN', `APPLICATION_${resource}_DEMAND_UNKNOWN`));
        if (q.available === null) require(has('UNKNOWN', `APPLICATION_${resource}_CAPACITY_UNKNOWN`));
        if (q.required !== null && q.available !== null && q.required > q.available) require(has('BLOCKER', `APPLICATION_${resource}_CAPACITY_INSUFFICIENT`));
        demand[resource] = q.required;
      }
      require(demands === null || equal(demands, demand)); demands = demand;
      require(row.status === statusFor(all));
    });
    return v;
  }
  function mount({document, window, drafts, session, destinations, settings, fetch, rejectSession = () => {}, timeoutMs = 15000}) {
    const $ = (id) => document.getElementById('app-compare-' + id);
    let record = null, profiles = new Map(), epoch = 0, busy = false, controller = null;
    const node = (tag, text) => { const n = document.createElement(tag); n.textContent = text; return n; };
    const status = (text) => { $('status').textContent = text; };
    function prepare() { return buildRequest(record, profiles, destinations(), settings()); }
    function controls() {
      let valid = false;
      try { prepare(); valid = !!session()?.token; } catch (_) { /* incomplete selection */ }
      $('submit').disabled = busy || !valid;
      $('cancel').disabled = !busy;
      const s = settings(), targets = destinations();
      $('settings').textContent = `${s.method || 'Choose a method'} · ${s.networkMode || 'Choose a network mode'} · ${s.dataMode || 'Choose a data mode'}. ` +
        targets.map((d) => `${d.environmentId}: generation ${d.generation}, capacity ${d.capacityKind ? d.capacityKind + '/' + d.capacityNativeId : 'not selected'}`).join('; ');
    }
    function invalidate(message = 'Selections changed. Compare again; previous advice is no longer displayed.') {
      epoch++; controller?.abort(); controller = null; busy = false;
      $('results').replaceChildren(); $('results').hidden = true; status(message); controls();
    }
    function setSource(value) {
      invalidate('Load a current saved draft, select destinations and enter a guest profile for every member.');
      record = null; profiles = new Map(); $('members').replaceChildren(); $('source').textContent = 'No unchanged current draft is selected.';
      try { if (value !== null) {
        const verified = drafts.validateRecord(value, value.environmentId, value.applicationGroupId, value.revision);
        require(!verified.sourceSuperseded); record = verified;
        $('source').textContent = `${record.applicationGroupId} · revision ${record.revision} · ${record.environmentId} generation ${record.generation}\nRecord ${record.recordDigest}\nObservation ${record.resultDigest}`;
        for (const m of record.proposal.draft.members) {
          const row = document.createElement('tr'), label = node('label', `Guest profile for ${m.workloadId}`), input = document.createElement('input');
          input.id = 'app-guest-' + m.workloadId; label.htmlFor = input.id; input.maxLength = 128; input.autocomplete = 'off'; input.spellcheck = false;
          profiles.set(m.workloadId, '');
          input.addEventListener('input', () => { profiles.set(m.workloadId, input.value.trim()); invalidate('Guest profile changed. Compare the exact selections again.'); });
          const cell = document.createElement('td'); cell.append(label, input);
          row.append(node('td', m.workloadId), node('td', m.nativeVm.join(' / ')), cell); $('members').append(row);
        }
      } } finally { controls(); }
    }
    function clear() { setSource(null); }
    function render(result, body) {
      const fragment = document.createElement('div'), review = result.applicationReview;
      fragment.append(node('p', `Owner review: ${review.status} · checked ${review.checkedAt}. No ownership or execution authority is granted.`));
      if (review.evidenceId) fragment.append(node('p', `Review evidence ${review.evidenceId}, revision ${review.evidenceRevision}, valid until ${review.expiresAt}.`));
      fragment.append(node('p', `Selection digest: ${result.selectionDigest}`));
      for (const [index, row] of result.assessments.entries()) {
        const card = document.createElement('article'); card.className = 'assessment-card assessment-' + row.status.toLowerCase();
        card.append(node('h3', row.environmentId + ' · ' + row.status + ' · assessment only'));
        const target = result.destinationInputs[index];
        card.append(node('p', `Pinned generation ${target.generation}; latest observed ${target.latestObservation.generation} (${target.latestObservation.collectionCompleteness}).`));
        card.append(node('p', `Capacity: ${row.capacityIdentity?.join(' / ') ?? 'Not selected'}. No reservation is held; staging and recovery footprint are excluded.`));
        const table = document.createElement('table'), head = document.createElement('tr');
        table.append(node('caption', 'Combined logical demand; memory and storage are bytes'));
        head.append(node('th', 'Resource'), node('th', 'Required'), node('th', 'Available')); table.append(head);
        for (const [name, q] of Object.entries(row.capacity.resources)) {
          const tr = document.createElement('tr'); tr.append(node('th', name), node('td', String(q.required ?? 'Unknown')), node('td', String(q.available ?? 'Unknown'))); table.append(tr);
        }
        card.append(table);
        for (const issue of row.issues) card.append(node('p', `${issue.severity} · ${issue.code}`));
        for (const member of row.members) {
          const details = document.createElement('details');
          details.append(node('summary', `${member.workloadId} · ${member.guestProfile} · ${member.status}`));
          details.append(node('p', member.nativeVm.join(' / ')));
          for (const issue of member.issues) details.append(node('p', `${issue.severity} · ${issue.code}`));
          card.append(details);
        }
        fragment.append(card);
      }
      $('results').replaceChildren(fragment); $('results').hidden = false;
      status(result.status === 'HELD_APPLICATION_REVIEW' ? 'Application review is held. No destination calculations were produced.' :
        `Compared ${body.memberProfiles.length} members across ${body.destinations.length} destinations. Advice is as of the displayed check, not migration approval.`);
    }
    async function compare() {
      if (busy) return;
      invalidate('Checking the selected application…');
      let body, retained, who;
      try { body = prepare(); retained = copy(record); who = {...session()}; require(who?.token && integer(who.version, 0)); }
      catch (_) { status('Load an unchanged current draft, two distinct destinations and valid profiles/modes. The limit is 200 member–destination pairs.'); return; }
      const version = epoch, abort = new AbortController(); controller = abort; busy = true; controls();
      const same = () => version === epoch && session()?.token === who.token && session()?.version === who.version && !abort.signal.aborted;
      const timer = setTimeout(() => abort.abort(), timeoutMs); let reader, response;
      try {
        const digest = await selectionDigest(body); if (!same()) return;
        response = await fetch('/v1/assessments/applications/compare', {method: 'POST', mode: 'same-origin', credentials: 'omit',
          cache: 'no-store', redirect: 'error', referrerPolicy: 'no-referrer', signal: abort.signal,
          headers: {Authorization: `Bearer ${who.token}`, Accept: 'application/json', 'Content-Type': 'application/json'}, body: JSON.stringify(body)});
        if (!same()) return;
        if (response.status === 401) { rejectSession(); clear(); return; }
        require(response.status === 200 && !response.redirected && response.body &&
          response.headers.get('content-type')?.split(';')[0].trim().toLowerCase() === 'application/json');
        const length = response.headers.get('content-length');
        require(length === null || /^[0-9]+$/.test(length) && Number(length) <= MAX_RESPONSE);
        reader = response.body.getReader(); const decoder = new TextDecoder('utf-8', {fatal: true}); let text = '', total = 0;
        while (true) {
          const chunk = await reader.read(); if (!same()) return; if (chunk.done) break;
          total += chunk.value.byteLength; require(total <= MAX_RESPONSE); text += decoder.decode(chunk.value, {stream: true});
        }
        text += decoder.decode(); require(length === null || Number(length) === total);
        const result = drafts.strictJson(text, MAX_RESPONSE);
        validateReport(result, body, digest, retained);
        if (same()) render(result, body);
      } catch (_) {
        if (version === epoch && session()?.version === who.version && session()?.token === who.token) {
          $('results').replaceChildren(); $('results').hidden = true;
          status('Comparison unavailable, expired, or inconsistent. No advice is shown. Reload current inputs before an explicit retry.');
        }
      } finally {
        clearTimeout(timer);
        try { if (reader) await reader.cancel(); else await response?.body?.cancel(); } catch (_) { /* already closed */ }
        finally { try { reader?.releaseLock(); } catch (_) { /* released */ } }
        if (version === epoch) { busy = false; controller = null; controls(); }
      }
    }
    $('form').addEventListener('submit', (event) => { event.preventDefault(); return compare(); });
    $('cancel').addEventListener('click', () => invalidate('Comparison cancelled. No report is retained; no migration was requested.'));
    window?.addEventListener('pagehide', clear); clear();
    return {setSource, invalidate, clear, compare};
  }
  return {mount, buildRequest, selectionDigest, validateReport, canonical};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = ApplicationComparisonWorkspace;
