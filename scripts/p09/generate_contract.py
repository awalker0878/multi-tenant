#!/usr/bin/env python3
"""Generate the frozen P09 v1 exact-tuple schema; --check detects contract drift."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def array(items, low=1, high=512):
    return {'type': 'array', 'items': items, 'minItems': low, 'maxItems': high, 'uniqueItems': True}


def schema():
    sha = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
    uid = {'type': 'string', 'format': 'uuid'}
    label = {'type': 'string', 'minLength': 1, 'maxLength': 160, 'pattern': '^[^\\u0000-\\u001f]*$'}
    integer = {'type': 'integer', 'minimum': 0, 'maximum': 9007199254740991}
    platforms = ['vmware', 'ahv', 'openstack']
    dimensions = ['installed_identity', 'compute_placement', 'storage_datasets', 'network_vpc',
                  'security_edge', 'guest_image', 'lifecycle_adoption', 'mobility', 'shared_services',
                  'resilience_operations', 'assurance_sovereignty']
    installed = obj({'platform': {'enum': platforms}, 'installation_id': uid, 'profile_sha256': sha,
                     'versions': obj({k: label for k in ['platform', 'api', 'network', 'storage']}),
                     'dimensions': obj({k: sha for k in dimensions})})
    constraints = obj({**{k: label for k in ['boot', 'disk_format', 'driver_profile', 'encryption', 'data_consistency']},
                       'guest_mutation': {'enum': ['copy_only', 'prohibited']}, 'writer_fencing': sha,
                       'target_write_recovery': sha, 'maximum_outage_seconds': integer,
                       'maximum_data_loss_seconds': integer})
    constraints['properties']['maximum_data_loss_bytes'] = integer
    route = obj({'id': uid, 'source': installed, 'target': installed,
                 'guest': {'enum': ['linux', 'windows', 'appliance']},
                 'method': {'enum': ['cold_export', 'rebuild_restore', 'application_delta', 'file_delta', 'block_replication']},
                 **{k + '_sha256': sha for k in ['guest_profile', 'topology', 'data', 'policy', 'services', 'recovery', 'artifacts']},
                 'constraints': constraints, 'requirement_ids': array({'enum': [f'R{i:02}' for i in range(1, 36)]}, 1, 35),
                 'exclusions': array(label, 0, 64)})
    route['properties']['guest_outcomes_sha256'] = sha
    route['allOf'] = [{'if': {'properties': {'guest': {'const': 'appliance'}}},
                       'then': {'properties': {'constraints': {'properties': {'guest_mutation': {'const': 'prohibited'}}}}}}]
    triggers = ['artifact', 'platform', 'api', 'backend', 'guest', 'method', 'policy', 'service', 'topology', 'recovery', 'ownership', 'expiry', 'revocation']
    result = obj({'schema_version': {'type': 'integer', 'const': 1}, 'id': uid,
                  'revision': integer | {'minimum': 1}, 'release_sha256': sha,
                  'owner_role': label, 'expires_at': integer | {'minimum': 1}, 'routes': array(route),
                  'operations': array({'enum': ['power_on', 'shutdown', 'power_off', 'resize_cpu', 'resize_memory',
                    'policy_change', 'patch', 'credential_rotation', 'scale_out', 'scale_in', 'ha_failover', 'relocate', 'adopt']}, 0, 13),
                  'deferred_directions': array({'enum': [a + '->' + b for a in platforms for b in platforms]}, 0, 9),
                  'retest_triggers': array({'enum': triggers}, len(triggers), len(triggers))})
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema',
            '$id': 'urn:multi-tenant:expansion-tranche:v1', 'title': 'P09 exact expansion tranche', **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    sha = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
    integer = {'type': 'integer', 'minimum': 0}
    label = {'type': 'string', 'minLength': 1, 'maxLength': 100}
    capability = obj({'operation': {'enum': ['power_on', 'shutdown', 'power_off', 'resize_cpu', 'resize_memory']},
                      'tuple_sha256': sha, 'route_sha256': sha})
    manifest = obj({'schema_version': {'type': 'integer', 'const': 1},
        'adapter_id': {'enum': ['vmware-lifecycle-v1', 'ahv-lifecycle-v1']}, 'version': label,
        **{k: sha for k in ['artifact_sha256', 'release_sha256', 'constraint_sha256', 'implementation_sha256']},
        'contracts': obj({k: {'const': v} for k, v in {'native_effect': '2', 'expansion': '1', 'journal': '1'}.items()}),
        'capabilities': array(capability), 'owner_role': label, 'not_before': integer, 'expires_at': integer,
        'retest_triggers': schema()['properties']['retest_triggers']})
    package = {'$schema': 'https://json-schema.org/draft/2020-12/schema',
               '$id': 'urn:multi-tenant:adapter-package:v1', 'title': 'Signed installed adapter package',
               **obj({'manifest': manifest, 'key_id': label,
                      'signature': {'type': 'string', 'pattern': '^[A-Za-z0-9+/]{86}==$'}})}
    for name, document in [('tranche-v1', schema()), ('adapter-package-v1', package)]:
        path = ROOT / f'contracts/schemas/expansion/{name}.json'
        rendered = json.dumps(document, indent=2) + '\n'
        if args.check:
            if path.read_text() != rendered:
                raise SystemExit('P09 contract drift: ' + name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered)


if __name__ == '__main__':
    main()
