"""Authentic pinned wire shapes; synthetic authority facts, never qualification."""
from copy import deepcopy
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import ssl
import threading

from provisioner.execution import readback_core as c
from provisioner.execution.run_files import digest, encoded, utcnow
from provisioner.migration.cold_selection import ColdVmSelection, FORMAT
from tests.provisioning.schema.test_enterprise_records import plan
from tests.provisioning.worker.tls_fixtures import TestPki
from tests.test_vsphere_observe import manifest, ref


def selection(directory,origin='https://vcenter.example.invalid',ca_sha='a'*64):
    approved = plan()
    source = approved['spec']['source']
    source['nativeScopeId']='datacenter-1'
    destination = approved['spec']['destination']
    destination.update(platformFamily='openstack',endpointId='openstack-01',nativeScopeId='project-01')
    config = manifest()['resources'][0]['expected']['config']
    config.update(firmware='bios',bootOptions={'efiSecureBootEnabled':False})
    config['hardware']['device'][0]['sharedBus']='noSharing'
    base = config['hardware']['device'][1]['backing']; base['sharing']='sharingNone'
    # Both original boot and data disks are retained, not a partial VM capture.
    disk2 = deepcopy(config['hardware']['device'][1]); disk2.update(key=2001,unitNumber=1)
    disk2['backing'].update(uuid='6000C290-fixture-second',fileName='[fixture-ds] vm/data.vmdk')
    config['hardware']['device'].append(disk2)
    snapshot = deepcopy(config)
    for disk in (device for device in snapshot['hardware']['device'] if device['_typeName']=='VirtualDisk'):
        parent = deepcopy(disk['backing'])
        disk['backing'].update(_typeName='VirtualDiskSeSparseBackingInfo',
            uuid=parent['uuid']+'-delta',fileName=parent['fileName'].replace('.vmdk','-000001.vmdk'),parent=parent)
    runtime = deepcopy(manifest()['resources'][0]['expected']['runtime']); runtime['powerState']='poweredOff'
    disks=[]
    for number,key in enumerate((2000,2001)):
        phases={phase:{'step_id':f'image-{number}-{phase.lower()}',
            'operation_id':f'image-op-{number}-{phase.lower()}',
            'lease_key':f'image-lease-{number}-{phase.lower()}'} for phase in ('CREATE','UPLOAD')}
        disks.append({'disk_id':f'disk-1-{number}','device_key':key,'nfc_key':f'nfc-disk-{number}',
            'logical_image_id':f'planned-image-{number}','max_export_bytes':4*1024**2,
            'max_output_bytes':4*1024**2,'phases':phases})
    expected = sum(2*row['max_export_bytes']+row['max_output_bytes'] for row in disks)
    body={'format':FORMAT,'guest_profile':'linux-ubuntu-2404','workload_id':approved['spec']['workloadId'],
        'workload_revision':approved['spec']['workloadRevision'],'source_scope':source,'destination_scope':destination,
        'source_snapshot_id':approved['spec']['sourceSnapshotId'],'resource_bundle_sha256':'b'*64,
        'vm':{'moid':'vm-1','snapshot_moid':'snapshot-1','current_config':config,'snapshot_config':snapshot,
            'runtime':runtime,'previous_owner':{'worker_id':'previous-worker','owner_epoch':1,'incident_id':'fence-1'}},
        'source_contact':{'vcenter_origin':origin,'vcenter_ca_sha256':ca_sha,'nfc_origins':[origin],'nfc_ca_sha256':ca_sha,
            **{field:{'origin':origin,'datacenter_id':'datacenter-1','session_manager_id':'SessionManager',
                'authorization_manager_id':'AuthorizationManager','principal':principal} for field,principal in
                (('writer_credential_profile','cold-native-writer'),('reader_credential_profile','cold-native-reader'))}},
        'destination_contact':{'identity_endpoint':origin+'/v3','glance_endpoint':origin+'/v2',
            'region':'RegionOne','interface':'internal','cloud_alias':'cold','ca_sha256':ca_sha},
        'export':{'step_id':'export-01','operation_id':'export-op-01','lease_key':'export-lease-01'},
        'disks':disks,'sandbox':{'tools':{'bwrap':'/usr/bin/bwrap','qemu_img':'/usr/bin/qemu-img',
            'prlimit':'/usr/bin/prlimit',**{name+'_sha256':'c'*64 for name in ('bwrap','qemu_img','prlimit')}},
            'limits':{'max_input_bytes':4*1024**2,'max_virtual_bytes':16*1024**3,
                'memory_bytes':268435456,'cpu_seconds':10,'wall_seconds':20}},
        'source_pool_id':'source-pool','image_pool_id':'image-pool',
        'capture_resources':{'stage_parent':str(directory),'cgroup':'/hosting/cold-fixture','block_device':'8:0',
            'limits':{'download_kib_per_second':1048576,'block_iops':1000,'stage_bytes':expected+4*1024**2,
                'expected_bytes':expected}}}
    return ColdVmSelection.from_record(body)


def capture(store,cold):
    """Standalone synthetic files with authentic sandbox/native report schemas."""
    directory=store.directory/'export-op-01';directory.mkdir(mode=0o700)
    rows={};manifest_rows=[]
    for row in cold.to_dict()['disks']:
        original=b'synthetic stream optimized VMDK '+row['disk_id'].encode()
        output=b'synthetic QCOW2 bytes '+row['disk_id'].encode()
        source=directory/(row['disk_id']+'.vmdk');source.write_bytes(original);source.chmod(0o400)
        converted=directory/(row['disk_id']+'.qcow2');converted.write_bytes(output);converted.chmod(0o400)
        virtual=cold.to_dict()['vm']['snapshot_config']['hardware']['device'][1]['capacityInBytes']
        conversion={'format':'hosting-isolated-disk-conversion/1','status':'CONVERTED_DISK_ARTIFACT_NOT_GUEST_QUALIFICATION',
            'sourceSha256':digest(original),'inputFormat':'vmdk','outputFormat':'qcow2','virtualSize':virtual,
            'outputSha256':digest(output),'outputBytes':len(output),
            'outputPath':str(converted.relative_to(store.directory)),
            'toolchain':{key:cold.to_dict()['sandbox']['tools'][key] for key in
                ('bwrap_sha256','qemu_img_sha256','prlimit_sha256')},
            'nativeContact':False,'mutationAuthorized':False,'guestBootQualified':False}
        rows[row['disk_id']]={'nfcKey':row['nfc_key'],'sourceSha256':digest(original),
            'inputBytes':len(original),'inputPath':str(source.relative_to(store.directory)),'conversion':conversion}
        manifest_rows.append({'key':row['nfc_key'],'size':len(original),'disk':True,'sha1':'legacy-only',
            'capacity':virtual,'checksum':digest(original),'checksumType':'sha256'})
    source_state={'selected-source':'native-original'}
    body={'format':'hosting-vsphere-cold-capture/1','coldSelectionDigest':cold.sha256,
        'exportOperationId':cold.to_dict()['export']['operation_id'],'nativeLeaseId':'nfclease-1',
        'sourceStateDigest':c.digest(source_state),'readyObservationDigest':'d'*64,'nativeManifest':manifest_rows,
        'disks':rows,'guestBootQualified':False}
    return body,source_state


def native_image(native_id,metadata,*,project='project-01',inputs=None):
    result=deepcopy(metadata)|{'id':native_id,'owner':project,'file':'/v2/images/'+native_id+'/file',
        'self':'/v2/images/'+native_id,'schema':'/v2/schemas/image','status':'queued','size':None,
        'virtual_size':None,'os_hash_algo':None,'os_hash_value':None}
    if inputs:
        result.update(status='active',size=inputs['output_bytes'],virtual_size=inputs['virtual_bytes'],
            os_hash_algo='sha512',os_hash_value=inputs['output_sha512'])
    return result


class NativeTls:
    """Real TLS with enumerated fixed routes and bounded synthetic responses."""
    def __init__(self):
        self.pki=TestPki();self.pki.issue('server');self.ca=self.pki.root/'ca.pem';self.ca.chmod(0o600)
        fixture=self
        class Handler(BaseHTTPRequestHandler):
            def exchange(self):
                self.connection.settimeout(3)
                size=int(self.headers.get('Content-Length','0'));require_size=0<=size<=8*1024**2
                if not require_size:self.send_error(413);return
                raw=self.rfile.read(size) if size else b''
                record={'method':self.command,'path':self.path,'body':raw,'headers':dict(self.headers)}
                fixture.requests.append(record)
                spec=fixture.routes.get((self.command,self.path),{'status':404,'body':{}})
                if callable(spec):spec=spec(record)
                data=spec.get('raw',encoded(spec.get('body',{})))
                if spec.get('before_response'):spec['before_response']()
                self.send_response(spec.get('status',200))
                self.send_header('Content-Type',spec.get('type','application/json'))
                if not spec.get('omit_length'):self.send_header('Content-Length',str(spec.get('length',len(data))))
                for key,value in spec.get('headers',[]):self.send_header(key,value)
                try:self.end_headers();self.wfile.write(data);self.wfile.flush()
                except (OSError,ssl.SSLError):pass
            do_GET=do_POST=do_PUT=do_DELETE=exchange
            def log_message(self,*args):pass
        self.routes={};self.requests=[]
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.minimum_version=ssl.TLSVersion.TLSv1_2
        tls.load_cert_chain(str(self.pki.root/'server.pem'),str(self.pki.root/'server.key'))
        self.server.socket=tls.wrap_socket(self.server.socket,server_side=True)
        self.origin='https://localhost:'+str(self.server.server_port)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def __enter__(self):return self
    def __exit__(self,*args):
        self.server.shutdown();self.server.server_close();self.thread.join(3);self.pki.close()


def token(cold,*,role='member',project='project-01'):
    return {'token':{'project':{'id':project},'application_credential':{'id':'dynamic-app'},
        'methods':['application_credential'],'roles':[{'name':role}],
        'expires_at':(utcnow()+timedelta(seconds=60)).isoformat(),
        'catalog':[{'type':'image','endpoints':[{'url':cold.to_dict()['destination_contact']['glance_endpoint'],
            'region_id':'RegionOne','interface':'internal'}]}]}}
