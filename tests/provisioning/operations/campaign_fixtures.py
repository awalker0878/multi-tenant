"""Synthetic route-chain custody fixtures; never exported as native evidence."""
from datetime import datetime, timezone
import hashlib
import json

from provisioner.allocations import capacity_evidence
from provisioner.domain.capabilities import CAPABILITIES
from provisioner.qualification import native, provenance, campaign, target_selection
from provisioner.qualification.action_gate import action_variant, bundle_digest
from provisioner.qualification.mobility import CampaignEndpoint, MobilityCampaign
from tests.test_platform_qualification import record, provenance_record
from tests.test_site_service_capacity import site_record
from tests.qualification_fixture_support import target_record, campaign_record

AS_OF = datetime(2026, 10, 3, tzinfo=timezone.utc)
REVISION = 'b' * 40


def fixture(artifact_digest='a' * 64, *, action=None):
    spec = MobilityCampaign(CampaignEndpoint('vmware-nsx', 'source-tuple', 'source-selection', 'SOURCE-CAMPAIGN'),
                           CampaignEndpoint('openstack', 'destination-tuple', 'destination-selection', 'DESTINATION-CAMPAIGN'),
                           'APPLICATION_REBUILD_RESTORE', 'linux-ubuntu-2404', 'app-fixture', 'job-fixture',
                           'c' * 64, REVISION, artifact_digest)
    bundle = {'qualification': native.load(), 'provenance': provenance.load(),
              'campaign': campaign.load(), 'targetSelection': target_selection.load(),
              'capacity': capacity_evidence.load()}
    for index in bundle.values():
        index['records'] = []
        index['reviewed_source_revision'] = REVISION
    source_scope = {'organizationId': 'org-fixture', 'tenantId': 'tenant-fixture',
                    'locationId': 'source-site', 'securityDomainId': 'wsd-fixture',
                    'endpointId': 'source-endpoint', 'nativeScopeId': 'source-scope',
                    'platformFamily': 'vmware'}
    destination_scope = {**source_scope, 'locationId': 'site-fixture', 'endpointId': 'destination-endpoint',
                         'nativeScopeId': 'destination-scope', 'platformFamily': 'openstack'}
    selection = {'sourceCommit': REVISION, 'driver': 'openstack-linux-rebuild/1',
                 'source': source_scope, 'destination': destination_scope, 'guestProfile': 'linux-ubuntu-2404'}
    rows = []
    for label, endpoint in (('source', spec.source), ('destination', spec.destination)):
        q = record(endpoint.platform, endpoint.product_tuple_id, caps=sorted(CAPABILITIES), assurance=('linux-ubuntu-2404',))
        q['id'] = 'QUAL-' + label.upper() + '-FIXTURE'
        rows.append(q)
        selection[label + 'Tuple'] = q['product_tuple']
    for number, (label, endpoint) in enumerate((('source', spec.source), ('destination', spec.destination))):
        q = rows[number]
        target = target_record(endpoint.platform, endpoint.product_tuple_id,
            selection_id=endpoint.selection_id, site_ref='controlled-site:' + label,
            cell_ref='controlled-cell:' + label, campaign_scope_ref='controlled-campaign-scope:' + label)
        required = spec.assertions()
        if action is not None:
            required = {**required, 'ACTION_' + action: 'OTHER'}
        refs = ['controlled-route-evidence:' + label + ':' + assertion for assertion in required]
        c = campaign_record(refs, endpoint.platform, endpoint.product_tuple_id,
            campaign_id=endpoint.campaign_id, selection_id=endpoint.selection_id,
            site_ref=target['scope']['site_ref'], cell_ref=target['scope']['cell_ref'],
            campaign_scope_ref=target['scope']['campaign_scope_ref'])
        c['required_assertions'] = list(required)
        for attempt, (assertion, observation_class) in zip(c['attempts'], required.items()):
            attempt.update(assertion_id=assertion, observation_class=observation_class,
                           attempt_id=label + '-' + assertion, variant_ref=spec.variant_ref)
            if observation_class == 'NEGATIVE_CONTROL':
                attempt['positive_control_attempt_ref'] = label + '-DISCOVERY_INDEPENDENT'
            if assertion.startswith('ACTION_'):
                attempt['variant_ref'] = action_variant(selection, action)
        q['evidence'] = [{'ref': a['evidence_ref'], 'sha256': a['artifact_sha256'],
                          'observed_at': a['observed_at'], 'expires_at': a['fresh_until'],
                          'test_set': 'CT-FIXTURE'} for a in c['attempts']]
        q['tested_limits'][0]['evidence_ref'] = refs[0]
        p = provenance_record(endpoint.platform, endpoint.product_tuple_id)
        p['provenance_id'] = 'PROV-' + label.upper()
        p['product_tuple'] = q['product_tuple']
        bundle['qualification']['records'].append(q)
        bundle['provenance']['records'].append(p)
        bundle['campaign']['records'].append(c)
        bundle['targetSelection']['records'].append(target)
    commissioned = site_record()
    q = rows[1]
    commissioned.update(platform=spec.destination.platform, product_tuple_id=spec.destination.product_tuple_id,
                        assurance_profiles=['linux-ubuntu-2404'], capacity_expires_at='2026-12-31T23:59:59Z')
    target = bundle['targetSelection']['records'][1]
    commissioned['qualification_binding'].update(
        qualification_record_id=q['id'], qualification_record_sha256=hashlib.sha256(json.dumps(
            q, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest(),
        approval_decision_ref=q['approval']['decision_ref'], supporting_campaign_id=spec.destination.campaign_id,
        selection_id=spec.destination.selection_id,
        site_ref=target['scope']['site_ref'], cell_ref=target['scope']['cell_ref'],
        campaign_scope_ref=target['scope']['campaign_scope_ref'])
    bundle['capacity']['records'] = [commissioned]
    selection['qualificationDigest'] = bundle_digest(bundle)
    return spec, bundle, selection
