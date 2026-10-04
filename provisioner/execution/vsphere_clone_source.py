"""Selected template identity/revision evidence; no source mutation or adoption."""
from provisioner.execution import readback_core as c
from provisioner.execution import vsphere_observe as vm
from provisioner.execution.run_files import require

FIELDS = {'_typeName', 'uuid', 'instanceUuid', 'template', 'changeVersion'}


def validate_info(info):
    c.exact_keys(info, FIELDS)
    require(info['_typeName'] == 'VirtualMachineConfigInfo' and info['template'] is True, 'Accepted template required')
    for key in ('uuid', 'instanceUuid'): vm.projection.uuid(info[key])
    c.text(info['changeVersion'])


def validate(sources, resources):
    require(isinstance(sources, list) and 1 <= len(sources) <= 20, 'Bounded clone sources required')
    ids = {r['moid'] for r in resources}
    uuids = {r['expected']['config']['uuid'] for r in resources}
    instances = {r['expected']['config']['instanceUuid'] for r in resources}
    result = {}
    for source in sources:
        c.exact_keys(source, {'moid', 'expected'}); vm.moid(source['moid'], 'vm'); validate_info(source['expected'])
        info = source['expected']
        require(source['moid'] not in ids and info['uuid'] not in uuids and info['instanceUuid'] not in instances, 'Source/destination identity overlap')
        ids.add(source['moid']); uuids.add(info['uuid']); instances.add(info['instanceUuid'])
        result[source['moid']] = source
    return result


def read(source, client):
    body, _ = client.get(vm.resource_target(source, 'config'))
    info = {key: body[key] for key in FIELDS if key in body}
    try: validate_info(info)
    except (ValueError, TypeError): return {}
    return info


def state(source, witness):
    status = 'UNKNOWN'; identity = False; mismatches = []
    try:
        c.exact_keys(witness, {'before', 'after'})
        for info in witness.values(): validate_info(info)
        identity = all(all(info[k] == source['expected'][k] for k in ('uuid', 'instanceUuid')) for info in witness.values())
        require(identity and c.digest(witness['before']) == c.digest(witness['after']), 'Unbound or changing template')
        mismatches = c.differences(witness['after'], source['expected'])
        status = 'DIFFERENT' if mismatches else 'MATCH'
    except (ValueError, TypeError, KeyError): mismatches = ['/source:unknown_or_changed']
    return dict(resource_key=source['moid'], identity_match=identity, config_status=status,
        progress='UNKNOWN' if status == 'UNKNOWN' else 'COMPLETE', mismatch_fields=mismatches,
        config_sha256=c.digest(witness), source_witness=witness, task_completion_observed=False,
        reason='TEMPLATE_IDENTITY_AND_REVISION_ONLY_NOT_IMAGE_ATTESTATION')
