"""Pinned VMware snapshot NFC capture, independent readback and isolated images.

Only an already selected, powered-off native snapshot is exported. The native
lease and manifest are retained under the existing original B11 intent. No
snapshot is guessed, an uncertain export is never resent, and no guest boots.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
import hashlib
import http.client
import os
from pathlib import Path
import re
import ssl
import stat
import time
from urllib.parse import urlsplit
from uuid import uuid4

from provisioner.controlplane.jobs.repository import _tenant
from provisioner.controlplane.reconciliation import NativeObservation, RecoveryHeld
from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.execution import image_sandbox, readback_core as c, vsphere_observe as vm
from provisioner.execution.nutanix_vm_observe import selected
from provisioner.execution.run_files import digest, encoded, load_private, private_path, read_private, require, utcnow, write_new
from .cold_authority import ColdExportAuthority
from .cold_selection import ColdVmSelection, backing_chain
from .vsphere_credentials import VsphereNativeCredentialOwner, VsphereNativeCredentialProfile

CAPTURE_FORMAT = 'hosting-vsphere-cold-capture/1'
OBSERVATION_FORMAT = 'hosting-vsphere-cold-export-observation/1'
READY_FORMAT = 'hosting-vsphere-cold-ready-observation/1'
_PREFIX = vm.PREFIX


def _ca(path, expected):
    raw = read_private(path)
    require(digest(raw) == expected, 'Native TLS trust differs from its approved private CA bundle')
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.verify_flags |= ssl.VERIFY_X509_STRICT
    context.load_verify_locations(cadata=raw.decode('ascii'))
    return context


def nfc_target(value, origins, vcenter_origin):
    """Server-issued lease URL; never redirect, proxy, wildcard host or bearer forwarding."""
    require(type(value) is str and 1 <= len(value) <= 8192 and '\\' not in value
            and not any(ord(character) < 33 or ord(character) > 126 for character in value),
            'Bounded server-issued NFC URL required')
    address = urlsplit(value)
    if address.hostname == '*':
        approved = urlsplit(vcenter_origin)
        host = '['+approved.hostname+']' if ':' in approved.hostname else approved.hostname
        netloc = host + (':'+str(address.port) if address.port else '')
        value = 'https://' + netloc + address.path + ('?'+address.query if address.query else '')
        address = urlsplit(value)
    require(address.scheme == 'https' and address.hostname and not address.username and not address.password
            and not address.fragment and address.path.startswith('/nfc/')
            and not address.path.startswith('//') and all(part not in {'.','..'} for part in address.path.split('/'))
            and not any(escape in address.path.lower() for escape in ('%2e','%5c','%00','%0a','%0d')),
            'NFC response escaped its fixed HTTPS lease download route')
    origin = c.origin('https://' + address.netloc)
    require(origin in origins, 'The native NFC host is not an approved HTTPS origin')
    return origin,address.path + ('?'+address.query if address.query else '')


def _nfc_certificate(thumbprint,leaf):
    # The approved CA and hostname remain mandatory. A native lease thumbprint
    # is an additional certificate identity check, never a TLS trust override.
    require(type(thumbprint) is str and isinstance(leaf,bytes) and leaf,
            'Actual TLS leaf and explicit native NFC certificate field required')
    if thumbprint == '':
        return  # The pinned native field documents an explicitly empty value.
    require(re.fullmatch(r'(?:[0-9A-Fa-f]{40}|[0-9A-Fa-f]{64}|(?:[0-9A-Fa-f]{2}:){19}[0-9A-Fa-f]{2}|(?:[0-9A-Fa-f]{2}:){31}[0-9A-Fa-f]{2})',thumbprint),
            'Native NFC certificate thumbprint has an unsupported exact representation')
    expected=thumbprint.replace(':','').lower()
    actual=hashlib.sha256(leaf).hexdigest() if len(expected)==64 else hashlib.sha1(leaf).hexdigest()
    require(actual == expected, 'The NFC TLS leaf differs from the original native lease certificate')


def _native_manifest(entries, cold, captures):
    rows = cold.to_dict()['disks']; expected = {row['nfc_key']:row for row in rows}
    require(type(entries) is list and len(entries) == len(expected), 'Complete native export manifest required')
    result, seen = [],set()
    config = cold.to_dict()['vm']['snapshot_config']
    disks = {disk['key']:disk for disk in config['hardware']['device'] if disk['_typeName'] == 'VirtualDisk'}
    for entry in entries:
        c.exact_keys(entry, {'key','sha1','size','disk','checksum','checksumType'},
                     {'_typeName','capacity','populatedSize'})
        key = entry['key']
        require(key in expected and key not in seen and entry['disk'] is True
                and entry['checksumType'] == 'sha256' and type(entry['checksum']) is str
                and c.HEX.fullmatch(entry['checksum']) and type(entry['size']) is int and entry['size'] > 0,
                'Native manifest has a missing, duplicate, foreign or non-SHA256 disk')
        seen.add(key); row = expected[key]; capture = captures[row['disk_id']]
        capacity = disks[row['device_key']]['capacityInBytes']
        require(entry['size'] == capture['inputBytes'] <= row['max_export_bytes']
                and entry['checksum'] == capture['sourceSha256']
                and type(entry.get('capacity')) is int and entry['capacity'] == capacity,
                'Downloaded bytes or virtual extent differ from the actual native snapshot manifest')
        require(type(entry['sha1']) is str and len(entry['sha1']) <= 128, 'Malformed native legacy checksum field')
        result.append({'key':key,'size':entry['size'],'disk':True,'capacity':capacity,'sha1':entry['sha1'],
                       'checksum':entry['checksum'],'checksumType':'sha256'})
    return sorted(result,key=lambda row:row['key'])


class _VsphereContact(c.ReadClient):
    def __init__(self,enrollment,cold,credentials,ca_bundle,*,cursor=None):
        require(isinstance(enrollment,(ColdExportAuthority,NativeReadEnrollment))
                and isinstance(cold,ColdVmSelection) and isinstance(credentials,VsphereNativeCredentialOwner),
                'Actual cold command or independently enrolled native read contact required')
        require(cursor is None or type(enrollment) is NativeReadEnrollment,
                'Only the independently enrolled read may reuse its original observation transaction')
        self.enrollment,self.cold,self.credentials,self.cursor = enrollment,cold,credentials,cursor
        self.ca_bundle=Path(ca_bundle);self.native_session=None
        contact = cold.to_dict()['source_contact']
        field='writer_credential_profile' if isinstance(enrollment,ColdExportAuthority) else 'reader_credential_profile'
        require(credentials.commands is enrollment.command
                and credentials.profile == VsphereNativeCredentialProfile(**contact[field]),
                'The native credential owner differs from its immutable cold worker/principal selection')
        super().__init__(contact['vcenter_origin'],contact['vcenter_origin'],None,None,{'/'},
                         timeout=10,budget=120,session_token='unacquired-no-native-use')
        self.context = _ca(ca_bundle,contact['vcenter_ca_sha256'])
        self.require_current()

    def require_current(self):
        options={'cursor':self.cursor} if self.cursor is not None else {}
        _grant,deadline = self.enrollment.require_current(**options)
        if self.native_session is not None:deadline=min(deadline,self.native_session.expires_at)
        require(deadline > utcnow(), 'The next native snapshot contact has expired current authority')
        # ReadClient enforces an additional absolute transport budget. Each
        # exchange gets only the live enrolled grant's remaining interval.
        self.timeout = min(10,(deadline-utcnow()).total_seconds())
        self.deadline = time.monotonic()+self.timeout
        return deadline

    def _exchange(self,kind,moid,property_name,*,method='GET',body=None,response_type=dict,void=False):
        allowed = {'VirtualMachine':({'config','runtime'},set()),
                   'VirtualMachineSnapshot':({'config','vm'},{'ExportSnapshot'}),
                   'HttpNfcLease':({'state','info'},{'HttpNfcLeaseProgress','HttpNfcLeaseGetManifest',
                       'HttpNfcLeaseSetManifestChecksumType','HttpNfcLeaseComplete'})}
        require(kind in allowed and property_name in allowed[kind][0 if method == 'GET' else 1]
                and method in {'GET','POST'}, 'Only fixed selected snapshot/lease native routes are implemented')
        vm.moid(moid, {'VirtualMachine':'vm','VirtualMachineSnapshot':'snapshot','HttpNfcLease':'nfclease'}[kind])
        selected_vm=self.cold.to_dict()['vm']
        require((kind != 'VirtualMachine' or moid == selected_vm['moid'])
                and (kind != 'VirtualMachineSnapshot' or moid == selected_vm['snapshot_moid']),
                'The cold native contact cannot select another VM or snapshot')
        if kind == 'HttpNfcLease' and isinstance(self.enrollment,ColdExportAuthority):
            require(self.enrollment.native_lease_id == moid,
                    'The native export contact must use its original actual response lease')
        require(isinstance(self.enrollment,ColdExportAuthority) or method == 'GET'
                or property_name == 'HttpNfcLeaseGetManifest', 'The independent reader cannot mutate an export lease')
        options={'cursor':self.cursor} if self.cursor is not None else {}
        self.enrollment.require_current(**options)
        self.context=_ca(self.ca_bundle,self.cold.to_dict()['source_contact']['vcenter_ca_sha256'])
        self.native_session=self.credentials.acquire_session(self.enrollment,
            native_id=selected_vm['moid'],origin=self.cold.to_dict()['source_contact']['vcenter_origin'],
            ca_file=self.ca_bundle,**options)
        self._auth_headers={'vmware-api-session-id':self.native_session.token}
        self.require_current()
        value,_etag = super()._request(method,_PREFIX+kind+'/'+moid+'/'+property_name,
                                      body,response_type=response_type,no_content=void)
        if property_name == 'ExportSnapshot':
            # An authentic late response is immutable business evidence. Keep
            # its actual native handle even when the next current check holds.
            vm.reference(value,'HttpNfcLease','nfclease')
            self.enrollment.accepted(value['value'])
        self.require_current()
        return value

    def source_state(self):
        selected_vm = self.cold.to_dict()['vm']; result = {}
        for kind,moid,field,expected in (
            ('VirtualMachine',selected_vm['moid'],'config',selected_vm['current_config']),
            ('VirtualMachine',selected_vm['moid'],'runtime',selected_vm['runtime']),
            ('VirtualMachineSnapshot',selected_vm['snapshot_moid'],'config',selected_vm['snapshot_config'])):
            raw = self._exchange(kind,moid,field)
            require(raw.get('keyId') is None and (field != 'runtime' or raw.get('question') is None),
                    'Native encryption or an unresolved VM question prohibits capture')
            actual = selected(raw,expected)
            if field == 'config':
                require(type(raw.get('hardware')) is dict and raw['hardware'].get('device') == expected['hardware']['device'],
                        'The complete native device/backing inventory changed')
            require(not c.differences(actual,expected), 'Selected source VM/snapshot native state changed')
            result[kind+'/'+field] = actual
        reference = self._exchange('VirtualMachineSnapshot',selected_vm['snapshot_moid'],'vm')
        vm.reference(reference,'VirtualMachine','vm')
        require(reference['value'] == selected_vm['moid'], 'The actual snapshot belongs to another native VM')
        return result

    def lease_state(self,lease_id):
        return self._exchange('HttpNfcLease',lease_id,'state',response_type=str)

    def lease_info(self,lease_id):
        result = self._exchange('HttpNfcLease',lease_id,'info')
        vm.reference(result.get('lease'),'HttpNfcLease','nfclease')
        vm.reference(result.get('entity'),'VirtualMachine','vm')
        require(result['lease']['value'] == lease_id and result['entity']['value'] == self.cold.to_dict()['vm']['moid']
                and type(result.get('leaseTimeout')) is int and 1 <= result['leaseTimeout'] <= 3600
                and type(result.get('totalDiskCapacityInKB')) is int and result['totalDiskCapacityInKB'] == sum(
                    disk['capacityInKB'] for disk in self.cold.to_dict()['vm']['snapshot_config']['hardware']['device']
                    if disk['_typeName'] == 'VirtualDisk'),
                'The native NFC lease does not cover the exact selected VM')
        return result

    def manifest(self,lease_id):
        return self._exchange('HttpNfcLease',lease_id,'HttpNfcLeaseGetManifest',method='POST',response_type=list)

    def export(self):
        require(isinstance(self.enrollment,ColdExportAuthority) and self.enrollment.claimed,
                'A native export must have its original claimed intent')
        self.enrollment.begin_native_send()
        reference = self._exchange('VirtualMachineSnapshot',self.cold.to_dict()['vm']['snapshot_moid'],
                                   'ExportSnapshot',method='POST')
        vm.reference(reference,'HttpNfcLease','nfclease')
        return reference['value']

    def checksums(self,lease_id,keys):
        require(set(keys) == {row['nfc_key'] for row in self.cold.to_dict()['disks']},
                'Native checksums must cover only the complete selected disk keys')
        return self._exchange('HttpNfcLease',lease_id,'HttpNfcLeaseSetManifestChecksumType',method='POST',
            body={'deviceUrlsToChecksumTypes':[{'key':key,'value':'sha256'} for key in sorted(keys)]},void=True)

    def progress(self,lease_id,percent):
        require(type(percent) is int and 0 <= percent <= 100, 'Integral bounded native lease progress required')
        self._exchange('HttpNfcLease',lease_id,'HttpNfcLeaseProgress',method='POST',body={'percent':percent},void=True)

    def complete(self,lease_id):
        self._exchange('HttpNfcLease',lease_id,'HttpNfcLeaseComplete',method='POST',void=True)


class ColdCaptureStore:
    """The installed control service's private immutable captured byte custody."""
    def __init__(self,directory):
        self.directory = private_path(directory,directory=True)

    def retain(self,document):
        sha = c.digest(document)
        write_new(self.directory/(sha+'.json'),encoded(document))
        return sha

    def load_verified(self,sha,cold):
        require(type(sha) is str and c.HEX.fullmatch(sha) and isinstance(cold,ColdVmSelection),
                'Exact original capture digest and protected cold selection required')
        value = load_private(self.directory/(sha+'.json'))
        c.exact_keys(value, {'format','coldSelectionDigest','exportOperationId','nativeLeaseId','sourceStateDigest',
                            'readyObservationDigest','nativeManifest','disks','guestBootQualified'})
        require(c.digest(value) == sha and value['format'] == CAPTURE_FORMAT
                and value['coldSelectionDigest'] == cold.sha256
                and value['exportOperationId'] == cold.to_dict()['export']['operation_id']
                and value['guestBootQualified'] is False and type(value['disks']) is dict
                and value['disks'].keys() == {row['disk_id'] for row in cold.to_dict()['disks']},
                'Original cold capture or complete disk custody changed')
        vm.moid(value['nativeLeaseId'],'nfclease')
        require(all(type(value[field]) is str and c.HEX.fullmatch(value[field]) for field in
                    ('sourceStateDigest','readyObservationDigest')),
                'Original source and independent ready-state observation commitments required')
        devices = {disk['key']:disk for disk in cold.to_dict()['vm']['snapshot_config']['hardware']['device']
                   if disk['_typeName'] == 'VirtualDisk'}
        for disk_id,row in value['disks'].items():
            c.exact_keys(row, {'nfcKey','sourceSha256','inputBytes','inputPath','conversion'})
            require(row['nfcKey'] == cold.disk(disk_id)['nfc_key'], 'The retained disk switched its immutable native NFC key')
            self._file(row['inputPath'],row['sourceSha256'],row['inputBytes'],cold.disk(disk_id)['max_export_bytes'])
            conversion = row['conversion']
            require(type(conversion) is dict and conversion.get('format') == 'hosting-isolated-disk-conversion/1'
                    and conversion.get('sourceSha256') == row['sourceSha256']
                    and conversion.get('inputFormat') == 'vmdk' and conversion.get('outputFormat') == 'qcow2'
                    and conversion.get('guestBootQualified') is False
                    and conversion.get('nativeContact') is False and conversion.get('mutationAuthorized') is False
                    and conversion.get('virtualSize') == devices[cold.disk(disk_id)['device_key']]['capacityInBytes']
                    and conversion.get('toolchain') == {key:cold.to_dict()['sandbox']['tools'][key] for key in
                        ('bwrap_sha256','qemu_img_sha256','prlimit_sha256')},
                    'The retained conversion lacks its selected mandatory isolated toolchain')
            self._file(conversion['outputPath'],conversion['outputSha256'],conversion['outputBytes'],
                       cold.disk(disk_id)['max_output_bytes'])
        _native_manifest(value['nativeManifest'],cold,value['disks'])
        return value

    def _file(self,path,sha,size,ceiling):
        require(type(path) is str and type(sha) is str and c.HEX.fullmatch(sha)
                and type(size) is int and 0 < size <= ceiling, 'Retained image extent and digest required')
        selected_path = Path(path)
        require(not selected_path.is_absolute() and '..' not in selected_path.parts
                and str(selected_path) == path, 'Retained image path escaped protected capture custody')
        result = private_path(self.directory/selected_path)
        descriptor = os.open(result,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            before = os.fstat(descriptor); actual = hashlib.sha256(); count = 0
            require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                    and before.st_mode & 0o777 == 0o400 and before.st_size == size,
                    'One sealed original retained image extent required')
            with os.fdopen(descriptor,'rb',closefd=False) as stream:
                while True:
                    chunk = stream.read(min(1048576,size-count+1))
                    if not chunk: break
                    count += len(chunk); require(count <= size, 'Retained image grew during custody verification')
                    actual.update(chunk)
            after = os.fstat(descriptor)
            require(count == size and actual.hexdigest() == sha
                    and (before.st_size,before.st_mtime_ns,before.st_ctime_ns) ==
                        (after.st_size,after.st_mtime_ns,after.st_ctime_ns),
                    'Original retained image bytes differ from their immutable capture')
        finally:
            os.close(descriptor)
        return result

    def image(self,sha,cold,disk_id):
        value = self.load_verified(sha,cold); row = value['disks'][disk_id]['conversion']
        return self._file(row['outputPath'],row['outputSha256'],row['outputBytes'],
                          cold.disk(disk_id)['max_output_bytes']),row


class VsphereColdCapture:
    def __init__(self,authority,*,credentials,ca_bundle,nfc_ca_bundle,store):
        require(isinstance(authority,ColdExportAuthority) and isinstance(credentials,VsphereNativeCredentialOwner)
                and credentials.commands is authority.command and isinstance(store,ColdCaptureStore),
                'Actual cold original authority, dynamic credential owners and protected capture store required')
        self.authority,self.credentials,self.store = authority,credentials,store
        self.ca_bundle,self.nfc_ca_bundle = Path(ca_bundle),Path(nfc_ca_bundle)

    def _download(self,client,lease_id,url,thumbprint,row,path,tls,percent):
        contact = self.authority.cold.to_dict()['source_contact']
        origin,target = nfc_target(url,contact['nfc_origins'],contact['vcenter_origin'])
        address = urlsplit(origin)
        connection = http.client.HTTPSConnection(address.hostname,address.port or 443,
            context=tls,timeout=self.authority.timeout())
        total = 0; sha = hashlib.sha256(); last_progress = time.monotonic()
        started = time.monotonic()
        resources = self.authority.cold.transfer_resources()
        try:
            # NFC tickets stay only in the server-issued URL. A vCenter session,
            # Vault credential, cookie or bearer is never forwarded to a host.
            connection.request('GET',target,headers={'Accept':'application/octet-stream',
                'Accept-Encoding':'identity','Connection':'close'})
            _nfc_certificate(thumbprint,connection.sock.getpeercert(binary_form=True))
            response = connection.getresponse(); lengths = response.headers.get_all('Content-Length',[])
            require(response.status == 200 and len(lengths) == 1 and lengths[0].isdigit()
                    and 0 < int(lengths[0]) <= row['max_export_bytes']
                    and not response.getheader('Transfer-Encoding')
                    and response.getheader('Content-Encoding','identity') == 'identity'
                    and response.headers.get_content_type() in {'application/octet-stream','application/x-vnd.vmware-streamvmdk'},
                    'Native NFC download has an unknown status, representation or bounded extent')
            expected = int(lengths[0]); socket = connection.sock
            with path.open('xb') as stream:
                os.chmod(path,0o400)
                while True:
                    timeout = self.authority.timeout()
                    client.require_current()
                    if socket and socket.fileno() >= 0: socket.settimeout(timeout)
                    chunk = response.read1(min(1048576,expected-total+1))
                    if not chunk: break
                    total += len(chunk)
                    require(total <= expected, 'NFC stream exceeded its checked extent')
                    sha.update(chunk); stream.write(chunk)
                    resources.require_current()
                    due = started + total/(resources.limits.download_kib_per_second*1024)
                    while time.monotonic() < due:
                        remaining = min(0.25,due-time.monotonic(),self.authority.timeout())
                        time.sleep(remaining)
                        if time.monotonic()-last_progress >= 1:
                            client.progress(lease_id,percent); last_progress = time.monotonic()
                    if time.monotonic()-last_progress >= 1:
                        client.progress(lease_id,percent); last_progress = time.monotonic()
                require(total == expected, 'Native NFC stream was truncated')
                stream.flush(); os.fsync(stream.fileno())
            self.authority.require_current()
            return {'sourceSha256':sha.hexdigest(),'inputBytes':total}
        finally:
            connection.close()

    def capture(self,reader):
        require(isinstance(reader,VsphereExportReadbackOwner) and reader.cold == self.authority.cold
                and reader.store is self.store and reader.enrollment.subject != self.authority.command.identity.subject,
                'A separately enrolled actual native export reader must retain the same original capture')
        authority,cold = self.authority,self.authority.cold
        tools,limits = cold.tools_and_limits(); tools.verify()
        contact = cold.to_dict()['source_contact']; tls = _ca(self.nfc_ca_bundle,contact['nfc_ca_sha256'])
        directory = self.store.directory/authority.row['operation_id']
        resources = cold.transfer_resources()
        require(resources.stage_parent == self.store.directory, 'Capture custody differs from its reserved staging owner')
        resources.enter_current(); resources.require_target(directory); resources.require_capacity(4*1024**2)
        require(not directory.exists() and not directory.is_symlink(),
                'Original capture already has retained bytes; observe it rather than exporting again')
        directory.mkdir(mode=0o700)
        authority.claim()
        try:
            client = _VsphereContact(authority,cold,self.credentials,self.ca_bundle)
            before = client.source_state(); lease_id = client.export(); authority.accepted(lease_id)
            end = time.monotonic()+min(60,authority.timeout(60))
            while client.lease_state(lease_id) == 'initializing':
                require(time.monotonic() < end, 'Native export lease did not become ready within its original interval')
                time.sleep(min(0.25,authority.timeout()))
            require(client.lease_state(lease_id) == 'ready', 'Native snapshot export is not ready')
            info = client.lease_info(lease_id); urls = info.get('deviceUrl')
            rows = cold.to_dict()['disks']; by_key = {row['nfc_key']:row for row in rows}
            require(type(urls) is list and len(urls) == len(rows), 'NFC lease does not cover the complete approved disk set')
            native_urls = {}
            for url in urls:
                c.exact_keys(url, {'key','url','sslThumbprint','disk'},
                             {'_typeName','importKey','targetId','datastoreKey','fileSize'})
                require(url['key'] in by_key and url['key'] not in native_urls and url['disk'] is True
                        and url.get('importKey') in (None,''), 'NFC lease includes an unselected, repeated or non-disk resource')
                nfc_target(url['url'],contact['nfc_origins'],contact['vcenter_origin'])
                require(type(url['sslThumbprint']) is str, 'Explicit native NFC certificate field required')
                native_urls[url['key']] = (url['url'],url['sslThumbprint'])
            client.checksums(lease_id,native_urls)
            captures = {}
            for number,row in enumerate(rows):
                path = directory/(row['disk_id']+'.vmdk')
                captured = self._download(client,lease_id,*native_urls[row['nfc_key']],row,path,tls,
                                          int(100*number/len(rows)))
                captures[row['disk_id']] = captured|{'nfcKey':row['nfc_key'],
                    'inputPath':str(path.relative_to(self.store.directory))}
                client.progress(lease_id,int(100*(number+1)/len(rows)))
            manifest = _native_manifest(client.manifest(lease_id),cold,captures)
            require(c.digest(client.source_state()) == c.digest(before), 'Native source changed during snapshot capture')
            # Independent native contact verifies manifest and lineage before
            # ending the lease; no worker-authored completion boolean is used.
            ready_sha = reader.retain_ready(lease_id,captures,manifest,before)
            client.complete(lease_id)
            require(client.lease_state(lease_id) == 'done', 'Native export task completion is unobserved')
            for row in rows:
                captured = captures[row['disk_id']]
                authority.require_current()
                converted = image_sandbox.convert(self.store.directory/captured['inputPath'],
                    directory/(row['disk_id']+'-isolated'),source_sha256=captured['sourceSha256'],
                    input_format='vmdk',tools=tools,limits=limits)
                require(converted['outputBytes'] <= row['max_output_bytes'], 'Converted image exceeds approved staged extent')
                converted['outputPath'] = str(Path(converted['outputPath']).relative_to(self.store.directory))
                captured['conversion'] = converted
            document = {'format':CAPTURE_FORMAT,'coldSelectionDigest':cold.sha256,
                'exportOperationId':authority.row['operation_id'],'nativeLeaseId':lease_id,
                'readyObservationDigest':ready_sha,
                'sourceStateDigest':c.digest(before),'nativeManifest':manifest,'disks':captures,'guestBootQualified':False}
            sha = self.store.retain(document)
            observation = reader.observe(sha)
            authority.registry.acknowledge_current(authority.command.context,authority.lease,authority.scope,
                authority.row['operation_id'],authority.command.identity,observation)
            return sha
        except Exception:
            authority.uncertain()
            raise


class VsphereExportReadbackOwner:
    """Independent current native session and original export/captured-byte check."""
    def __init__(self,*,enrollment,credentials,cold,store,ca_bundle,evidence_directory,exclusion_owner):
        require(type(enrollment) is NativeReadEnrollment and isinstance(cold,ColdVmSelection)
                and isinstance(store,ColdCaptureStore)
                and isinstance(credentials,VsphereNativeCredentialOwner) and credentials.commands is enrollment.command
                and enrollment.scope == PlanScopeFromCold(cold)
                and callable(getattr(exclusion_owner,'verify_owner_exclusion',None)),
                'Independent enrolled VMware reader, protected captured custody and original exclusion owner required')
        self.enrollment,self.credentials,self.cold,self.store = enrollment,credentials,cold,store
        self.ca_bundle = Path(ca_bundle); self.directory = private_path(evidence_directory,directory=True)
        self.exclusion_owner = exclusion_owner

    def _contact(self,*,cursor=None):
        return _VsphereContact(self.enrollment,self.cold,self.credentials,self.ca_bundle,cursor=cursor)

    def retain_ready(self,lease_id,captures,manifest,source_state):
        client = self._contact()
        require(client.lease_state(lease_id) == 'ready' and c.digest(client.source_state()) == c.digest(source_state),
                'Independent native export state or selected backing lineage differs')
        native = _native_manifest(client.manifest(lease_id),self.cold,captures)
        require(native == manifest, 'Independent native NFC manifest differs from the captured byte commitments')
        # Complete releases the lease. GetManifest must not be replayed against
        # a completed lease; retain this independently obtained native checksum
        # witness before the separate original completion command.
        at = utcnow()
        record = {'format':READY_FORMAT,'coldSelectionDigest':self.cold.sha256,
            'operationId':self.cold.to_dict()['export']['operation_id'],'nativeLeaseId':lease_id,
            'observerSubject':self.enrollment.subject,'readGrantId':self.enrollment.command.grant.grant_id,
            'observedAt':at.isoformat(),'sourceStateDigest':c.digest(source_state),
            'nativeManifestDigest':c.digest(native),'capturedByteDigests':{
                key:{field:row[field] for field in ('nfcKey','sourceSha256','inputBytes')}
                for key,row in captures.items()}}
        sha = c.digest(record); write_new(self.directory/(sha+'.json'),encoded(record))
        return sha

    def _completed(self,value,*,cursor=None):
        ready = load_private(self.directory/(value['readyObservationDigest']+'.json'))
        require(c.digest(ready) == value['readyObservationDigest'] and ready['format'] == READY_FORMAT
                and ready['coldSelectionDigest'] == self.cold.sha256
                and ready['operationId'] == value['exportOperationId']
                and ready['nativeLeaseId'] == value['nativeLeaseId']
                and ready['observerSubject'] == self.enrollment.subject
                and ready['sourceStateDigest'] == value['sourceStateDigest']
                and ready['nativeManifestDigest'] == c.digest(value['nativeManifest'])
                and ready['capturedByteDigests'] == {key:{field:row[field] for field in
                    ('nfcKey','sourceSha256','inputBytes')} for key,row in value['disks'].items()},
                'Original independent ready-state native checksum/lineage evidence changed')
        client = self._contact(cursor=cursor); state = client.source_state()
        require(client.lease_state(value['nativeLeaseId']) == 'done'
                and c.digest(state) == value['sourceStateDigest'],
                'Native export completion or retained source configuration changed')
        return state

    def observe(self,capture_sha):
        value = self.store.load_verified(capture_sha,self.cold); self._completed(value)
        at = utcnow()
        record = {'format':OBSERVATION_FORMAT,'captureDigest':capture_sha,'coldSelectionDigest':self.cold.sha256,
            'operationId':value['exportOperationId'],'nativeLeaseId':value['nativeLeaseId'],
            'observerSubject':self.enrollment.subject,'readGrantId':self.enrollment.command.grant.grant_id,
            'observedAt':at.isoformat(),'sourceStateDigest':value['sourceStateDigest'],
            'nativeManifestDigest':c.digest(value['nativeManifest']),
            'readyObservationDigest':value['readyObservationDigest']}
        sha = c.digest(record); write_new(self.directory/(sha+'.json'),encoded(record))
        return NativeObservation('cold-export-read-'+uuid4().hex,sha,self.enrollment.subject,
                                 value['nativeLeaseId'],'EFFECT_PRESENT',True,at)

    def verify_native_observation(self,cursor,operation,observation):
        self.enrollment.require_current(cursor=cursor)
        record = load_private(self.directory/(observation.evidence_digest+'.json'))
        require(c.digest(record) == observation.evidence_digest and record['format'] == OBSERVATION_FORMAT
                and record['coldSelectionDigest'] == self.cold.sha256 and record['operationId'] == operation.operation_id
                and record['nativeLeaseId'] == operation.native_task_id == observation.native_task_id
                and observation.outcome == 'EFFECT_PRESENT' and observation.native_quiesced
                and record['observerSubject'] == observation.observer_subject == self.enrollment.subject
                and record['observedAt'] == observation.observed_at.isoformat()
                and operation.binding == self.cold.binding() and operation.operation_kind == 'SNAPSHOT_EXPORT'
                and operation.worker_id != observation.observer_subject,
                'Independent export observation changed its original native operation or reader')
        value = self.store.load_verified(record['captureDigest'],self.cold)
        state = self._completed(value,cursor=cursor)
        require(c.digest(state) == value['sourceStateDigest'] == record['sourceStateDigest']
                and c.digest(value['nativeManifest']) == record['nativeManifestDigest']
                and value['readyObservationDigest'] == record['readyObservationDigest'],
                'Original exported source or retained manifest changed during acceptance')

    def verify_owner_exclusion(self,cursor,lease,scope,evidence):
        self.exclusion_owner.verify_owner_exclusion(cursor,lease,scope,evidence)


def PlanScopeFromCold(cold):
    from provisioner.controlplane.authority.model import PlanScope
    return PlanScope.from_record(cold.to_dict()['source_scope'])
