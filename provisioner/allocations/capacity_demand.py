"""Bind owned workload shapes and placements to a current capacity reservation."""
from provisioner.execution import readback_core as c
from provisioner.allocations import capacity_owner as capacity
import re
from provisioner.execution.run_files import current_window,load_private,require

PLACEMENT={'nutanix':{'cluster_id','project_id','storage_container_id'},
           'vmware':{'resource_pool_id','datastore_id','storage_policy_id'},
           'openstack':{'compute_availability_zone','storage_availability_zone','volume_type'}}
GIB=2**30
MIB=2**20


def integer(value,minimum=0):
    require(type(value) is int and minimum<=value<=10**9,'Bounded integral native sizing required')
    return value


def validate_catalog(catalog,*,current=True):
    c.exact_keys(catalog,{'format','pool_id','origin','native_id','platform','site_key','placements','flavors',
                          'provider_selector','cloud_sha256','valid_from','valid_until','acceptance_ref'})
    require(catalog['format']=='hosting-capacity-sizing/1' and catalog['platform'] in PLACEMENT,'Unknown sizing catalogue')
    c.identifier(catalog['pool_id']); c.identifier(catalog['site_key']); c.text(catalog['native_id']); c.text(catalog['acceptance_ref'])
    require(c.origin(catalog['origin'])==catalog['origin'],'Canonical capacity origin required')
    current_window(catalog,None if current else c.timestamp(catalog['valid_from']))
    selector='openstack_cloud' if catalog['platform']=='openstack' else 'platform_endpoint'
    c.exact_keys(catalog['provider_selector'],{selector}); c.text(catalog['provider_selector'][selector])
    require(isinstance(catalog['cloud_sha256'],str) and re.fullmatch('[0-9a-f]{64}',catalog['cloud_sha256'])
            if catalog['platform']=='openstack' else catalog['cloud_sha256'] is None,
            'Exact OpenStack cloud-file binding required only for OpenStack')
    require(isinstance(catalog['placements'],list) and 1<=len(catalog['placements'])<=1000,'Exact accepted placement set required')
    seen=set()
    for placement in catalog['placements']:
        c.exact_keys(placement,PLACEMENT[catalog['platform']])
        for value in placement.values(): c.text(value)
        require(c.digest(placement) not in seen,'Duplicate capacity placement'); seen.add(c.digest(placement))
    require(isinstance(catalog['flavors'],dict),'Explicit flavor catalogue required')
    require(bool(catalog['flavors'])==(catalog['platform']=='openstack'),'Flavor sizing belongs only to OpenStack')
    for identity,flavor in catalog['flavors'].items():
        c.text(identity); c.exact_keys(flavor,{'vcpu','ram_mib','root_gib','ephemeral_gib','swap_mib'})
        integer(flavor['vcpu'],1); integer(flavor['ram_mib'],1)
        for key in ('root_gib','ephemeral_gib','swap_mib'):
            require(type(flavor[key]) is int and flavor[key]==0,
                    'Selected retained-volume profile requires zero local root, ephemeral and swap disks')


def derive(inputs,catalog,*,current=True):
    validate_catalog(catalog,current=current); platform=catalog['platform']
    scope={key:inputs[key] for key in ('environment_key','site_key','tenant_key','wsd_key')}; scope['platform']=platform
    for value in scope.values(): c.identifier(value)
    require(scope['site_key']==catalog['site_key'],'Workload sizing belongs to another site')
    require(all(inputs.get(key)==value for key,value in catalog['provider_selector'].items()),
            'Workload provider endpoint or cloud selector changed')
    require(isinstance(inputs['members'],dict) and 1<=len(inputs['members'])<=1000,'Bounded owned workload members required')
    members={}; total={'vcpu':0,'memory_mb':0,'storage_gb':0}
    for name,member in inputs['members'].items():
        c.identifier(name); require(isinstance(member,dict),'Typed workload member required')
        placement={key:member[key] for key in PLACEMENT[platform]}
        require(placement in catalog['placements'],'Workload placement is outside the accepted capacity pool')
        def size(key,default,minimum=0): return integer(default if member.get(key) is None else member[key],minimum)
        storage=(size('boot_disk_gib',40,1)+size('data_disk_gib',0))*GIB
        if platform=='openstack':
            identity=member['flavor_id']; require(identity in catalog['flavors'],'Unknown native flavor sizing')
            shape=catalog['flavors'][identity]; cpu=shape['vcpu']; memory=shape['ram_mib']*MIB
        else:
            identity=None; cpu=size('vcpu',2,1); memory=size('memory_gib',4,1)*GIB
        members[name]={'placement':placement,'flavor_id':identity,'vcpu':cpu,'memory_bytes':memory,'storage_bytes':storage}
        total['vcpu']+=cpu
        # Capacity's MB/GB fields are decimal. Round each VM upward, never undercharge.
        total['memory_mb']+=(memory+10**6-1)//10**6
        total['storage_gb']+=(storage+10**9-1)//10**9
    capacity.units(total)
    return {'format':'hosting-capacity-demand/1','scope':scope,'pool_id':catalog['pool_id'],
            'sizing_sha256':c.digest(catalog),'units':total,'members':members}


def bind_request(request,inputs,catalog,*,current=True):
    capacity.validate_request(request); demand=derive(inputs,catalog,current=current)
    require(request['scope']==demand['scope'] and request['pool_id']==demand['pool_id'],'Foreign workload reservation')
    require(all(request['units'][key]>=demand['units'][key] for key in capacity.UNITS),
            'Reserved capacity is smaller than actual workload demand')
    return demand


def owner_binding(path,request,catalog,*,require_live):
    validate_catalog(catalog)
    with capacity.database(path) as db:
        rows=capacity.verify_events(db)
        envelope=c.strict_loads(db.execute('SELECT body FROM envelope WHERE singleton=1').fetchone()[0])
        capacity.validate_envelope(envelope)
        require(envelope['owner_id']==request['owner_id'] and request['pool_id']==catalog['pool_id'],
                'Wrong capacity owner or sizing pool')
        pool=envelope['pools'][request['pool_id']]
        require(all(pool[key]==catalog[key] for key in ('origin','native_id','platform','site_key')),
                'Sizing catalogue belongs to another native pool')
        if require_live:
            row=next((r for r in rows if r[0]==request['reservation_id']),None)
            require(row is not None and row[2] in capacity.LIVE and c.digest(c.strict_loads(row[1]))==c.digest(request),
                    'Workload reservation is missing, changed or released')
            return c.strict_loads(row[4])


def check_ancestors(step,plan,base,inputs,*,cloud_sha256=None):
    """Every selected reserve stage must retain its exact demand through plan/apply."""
    ancestors=set(step['needs'])
    for previous in reversed(plan['steps']):
        if previous['id'] in ancestors: ancestors.update(previous['needs'])
    for previous in plan['steps']:
        if previous['id'] not in ancestors or previous['kind']!='capacity': continue
        directory=base/'steps'/previous['id']; packet=load_private(directory/'packet.json')
        if packet['parameters']['action']!='reserve': continue
        require((directory/'demand.json').exists(),'Workload provisioning requires sizing bound to its capacity reservation')
        request=load_private(directory/'capacity-request.json'); catalog=load_private(directory/'sizing.json')
        require(cloud_sha256==catalog['cloud_sha256'],'Workload cloud configuration differs from the accepted capacity pool')
        demand=bind_request(request,inputs,catalog)
        require(demand==load_private(directory/'demand.json'),'Workload shape, membership or placement changed after reservation')
        owner_binding(packet['parameters']['database'],request,catalog,require_live=True)
