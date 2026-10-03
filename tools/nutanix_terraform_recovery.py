"""Bind existing AHV power/NIC lifecycle plans to activity evidence; no ledger release."""
from provisioner.execution import readback_core as c
from provisioner.execution import lifecycle_transition as lifecycle
from tools import nutanix_vm_activity_observe as activity
from provisioner.execution.plan_review import has_true
from provisioner.execution.run_files import require

OBSERVED_PLAN_FIELDS = {'id', 'ext_id', 'name', 'power_state', 'num_sockets', 'num_cores_per_socket',
                        'memory_size_bytes', 'cluster', 'project', 'categories', 'nics', 'disks'}
COMPUTED_FIELDS = {'update_time', 'status'}


def valid_mask(value):
    if type(value) is bool: return True
    if isinstance(value, dict): return all(valid_mask(v) for v in value.values())
    if isinstance(value, list): return all(valid_mask(v) for v in value)
    return False


def plan_expectation(expected):
    """Selected pinned-provider 2.4.2 fields; other unchanged settings stay outside readback coverage."""
    result = dict(id=expected['extId'], ext_id=expected['extId'], name=expected['name'],
        power_state=expected['powerState'], num_sockets=expected['numSockets'],
        num_cores_per_socket=expected['numCoresPerSocket'], memory_size_bytes=expected['memorySizeBytes'])
    for key in ('cluster', 'project'): result[key] = [{'ext_id': expected[key]['extId']}]
    result['categories'] = [{'ext_id': r['extId']} for r in expected['categories']]
    result['nics'] = []
    for nic in expected['nics']:
        backing = nic['nicBackingInfo']; network = nic['nicNetworkInfo']; ipv4 = network['ipv4Config']
        result['nics'].append(dict(ext_id=nic['extId'], nic_backing_info=[{'virtual_ethernet_nic': [dict(
            is_connected=backing['isConnected'], mac_address=backing['macAddress'], model=backing['model'])]}],
            nic_network_info=[{'virtual_ethernet_nic_network_info': [dict(nic_type=network['nicType'],
                subnet=[{'ext_id': network['subnet']['extId']}], ipv4_config=[dict(should_assign_ip=ipv4['shouldAssignIp'],
                    ip_address=[{'value': ipv4['ipAddress']['value'], 'prefix_length': ipv4['ipAddress']['prefixLength']}])])]}]))
    result['disks'] = [dict(ext_id=d['extId'], disk_address=[dict(bus_type=d['diskAddress']['busType'], index=d['diskAddress']['index'])],
        backing_info=[{'vm_disk': [dict(disk_ext_id=d['backingInfo']['diskExtId'], disk_size_bytes=d['backingInfo']['diskSizeBytes'],
            storage_container=[{'ext_id': d['backingInfo']['storageContainer']['extId']}])]}]) for d in expected['disks']]
    return result


def bind_member(expected, name, member, stage):
    for key, default, minimum in [('vcpu', 2, 1), ('memory_gib', 4, 1), ('boot_disk_gib', 40, 1), ('data_disk_gib', 0, 0)]:
        require(type(member.get(key, default)) is int and member.get(key, default) >= minimum, 'Typed member capacity required')
    target = stage == 'bootstrap'
    values = dict(name=name, powerState='ON' if target else 'OFF', numSockets=1,
                  numCoresPerSocket=member.get('vcpu', 2), memorySizeBytes=member.get('memory_gib', 4)*1073741824,
                  cluster={'extId': member['cluster_id']}, project={'extId': member['project_id']},
                  categories=[{'extId': member['security_category_id']}])
    require(not c.differences(expected, values), 'AHV expectations differ from sealed member inputs')
    require(len(expected['nics']) == 1, 'One owned AHV NIC required')
    nic = expected['nics'][0]
    require(nic['nicBackingInfo']['isConnected'] is target and nic['nicNetworkInfo']['subnet']['extId'] == member['subnet_id']
            and nic['nicNetworkInfo']['ipv4Config']['ipAddress']['value'] == member['ipv4_address'], 'AHV NIC expectation differs from lifecycle')
    sizes = [member.get('boot_disk_gib', 40)] + ([member['data_disk_gib']] if member.get('data_disk_gib', 0) else [])
    require(len(expected['disks']) == len(sizes), 'Retained disk coverage differs from sealed inputs')
    for index, (disk, size) in enumerate(zip(expected['disks'], sizes)):
        require(disk['diskAddress'] == {'busType': 'SCSI', 'index': index}
                and disk['backingInfo']['diskSizeBytes'] == size*1073741824
                and disk['backingInfo']['storageContainer']['extId'] == member['storage_container_id'], 'Retained disk expectation differs')


def bind_plan(plan, inputs, manifest, transition, *, attempted_at):
    require(manifest.get('profile') == activity.PROFILE, 'AHV visible activity required; known-task-only evidence cannot recover an attempt')
    activity.validate(manifest)
    require(plan.get('format_version') == '1.2' and plan.get('complete') is True and not plan.get('errored')
            and not plan.get('deferred_changes') and not plan.get('resource_drift')
            and all(isinstance(check, dict) and check.get('status') == 'pass' for check in plan.get('checks', [])), 'Unresolved saved plan')
    require(transition['scope']['platform'] == 'nutanix' and transition['scope']['phase'] == 'workloads'
            and c.digest(transition['requested_inputs']) == c.digest(inputs), 'AHV lifecycle scope or inputs differ')
    # This is historical consistency checking only. Current prepare/apply paths
    # continue to validate against their live clock and separate apply authority.
    lifecycle.plan_bindings(plan, transition, as_of=c.timestamp(attempted_at))
    wanted = transition['resources']; resources = {r['ext_id']: r for r in manifest['resources']}
    actual = {}; ids = set()
    for item in plan['resource_changes']:
        require(item.get('address') in wanted and item['address'] not in actual and item.get('mode') == 'managed'
                and item.get('type') == 'nutanix_virtual_machine_v2'
                and item.get('provider_name') == 'registry.terraform.io/nutanix/nutanix', 'Only exact owned AHV VMs supported')
        spec = wanted[item['address']]; identity = spec['id']; change = item['change']; unknown = change.get('after_unknown', {})
        require(valid_mask(unknown) and not any(has_true(v) for k, v in unknown.items() if k not in COMPUTED_FIELDS), 'Unresolved AHV configuration')
        require(identity in resources and identity not in ids, 'AHV plan and native coverage differ')
        if change['actions'] == ['no-op']:
            lifecycle.unchanged(change['before'], change['after'], COMPUTED_FIELDS)
        expected = resources[identity]['expected']; member = inputs['members'][spec['member']]
        bind_member(expected, spec['member'], member, transition['target_stage'])
        after = change['after']
        require(not c.differences(after, plan_expectation(expected)), 'Planned AHV configuration differs from native expectations')
        for field, value in [('host', [{'ext_id': expected['host']['extId']}]), ('tenant_id', expected['tenantId'])]:
            if field in after: require(not c.differences(after[field], value), 'Known AHV placement or tenant metadata differs')
        ids.add(identity); actual[item['address']] = identity
    require(set(actual) == set(wanted) and ids == set(resources), 'Incomplete AHV plan or native scope')
    return actual
