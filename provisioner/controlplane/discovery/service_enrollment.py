"""Exact installed service/interpreter/store facts pinned by an external owner.

Capturing facts does not enroll a service. The commissioned budget/monitor owner
pins the manifest digest separately. A restart, package replacement, store move,
interpreter change or host move cannot silently reuse that enrollment.
"""
from dataclasses import dataclass
import hashlib
from importlib import metadata
import os
from pathlib import Path
import re
import stat
import sys

from .collector_settings import protected_path
from .model import _id, _json
from .native_credentials import decode_json, read_protected
from .review_files import private_parent
from .trust import _keys


def _digest(raw):return hashlib.sha256(raw).hexdigest()


def _public_file(path,limit):
    path=protected_path(str(path))
    # Parent links and writable ancestors must not redirect the actual program
    # between verification and dispatch. These are public code, not secrets.
    for parent in (path.parent,*path.parents):
        value=os.lstat(parent)
        if (not stat.S_ISDIR(value.st_mode) or value.st_uid not in (0,os.geteuid())
                or value.st_mode&0o022 and not (value.st_uid==0 and value.st_mode&stat.S_ISVTX)):
            raise PermissionError('Installed service ancestor is unsafe')
    return read_protected(path,limit,secret=False)


def package_facts():
    distribution=metadata.distribution('hosting-provisioner')
    root=Path(distribution.locate_file('')).resolve(strict=True)
    import provisioner
    if Path(provisioner.__file__).resolve(strict=True).parent!=root/'provisioner':
        raise PermissionError('Imported discovery owner differs from the installed distribution')
    files=distribution.files
    if files is None:raise PermissionError('Installed package file record is unavailable')
    records=[];listed=set();metadata_files=[]
    for item in files:
        relative=Path(str(item))
        if not relative.parts:continue
        selected=relative.parts[0]=='provisioner'
        info=relative.parts[0].endswith('.dist-info') and relative.name in ('METADATA','RECORD','entry_points.txt','WHEEL')
        if not selected and not info:continue
        if relative.is_absolute() or '..' in relative.parts:
            raise PermissionError('Installed package record escapes its root')
        path=root/relative
        records.append([str(relative),_digest(_public_file(path,8*1024*1024))])
        if selected:listed.add(str(relative))
        else:metadata_files.append(relative.name)
        if len(records)>10000:raise PermissionError('Installed package exceeds the enrollment bound')
    actual=set()
    for path in (root/'provisioner').rglob('*'):
        info=os.lstat(path)
        if stat.S_ISDIR(info.st_mode):continue
        relative=str(path.relative_to(root));actual.add(relative)
        if len(actual)>10000:raise PermissionError('Installed package exceeds the enrollment bound')
        if relative not in listed:
            # Installed bytecode is also executable code. If pip did not list a
            # generated cache file, retain its actual identity instead of
            # excluding it from commissioning. Units disable further writes.
            if path.suffix!='.pyc':raise PermissionError('Installed package has unrecorded executable content')
            records.append([relative,_digest(_public_file(path,8*1024*1024))])
    if (not listed or not listed<=actual or not {'METADATA','RECORD','WHEEL'}<=set(metadata_files)
            or len({value[0] for value in records})!=len(records)):
        raise PermissionError('Installed package file record is incomplete')
    return {'name':'hosting-provisioner','version':distribution.version,'root':str(root),
            'contentDigest':_digest(_json(sorted(records)).encode('ascii'))}


def interpreter_facts():
    interpreter=Path(sys.executable).resolve(strict=True)
    return {'path':str(interpreter),'contentDigest':_digest(_public_file(interpreter,64*1024*1024)),
            'version':sys.version}


def capture_service_facts(service_id,stores):
    if not _id(service_id) or not isinstance(stores,dict) or not 1<=len(stores)<=16:
        raise ValueError('Exact service and retained store selection is required')
    selected=[]
    for name,value in sorted(stores.items()):
        if not _id(name):raise ValueError('Invalid retained store name')
        path=protected_path(str(value))
        with private_parent(str(path/'enrollment-probe')) as (parent,_):
            info=os.fstat(parent)
            if info.st_uid!=os.geteuid():raise PermissionError('Retained store is not owned by this service')
            selected.append({'name':name,'path':str(path),'device':info.st_dev,'inode':info.st_ino,
                             'uid':info.st_uid,'mode':stat.S_IMODE(info.st_mode)})
    return {'format':'hosting-discovery-service-enrollment/1','serviceId':service_id,
            'hostIdentityDigest':_digest(_public_file(Path('/etc/machine-id'),4096)),
            'uid':os.geteuid(),'python':interpreter_facts(),'package':package_facts(),'stores':selected}


@dataclass(frozen=True,slots=True)
class ServiceEnrollment:
    path:Path
    digest:str
    document_json:str

    @classmethod
    def from_file(cls,path,expected_digest):
        if not isinstance(expected_digest,str) or re.fullmatch('[0-9a-f]{64}',expected_digest) is None:
            raise ValueError('An externally pinned service manifest digest is required')
        path=protected_path(str(path));raw=read_protected(path,65536)
        if _digest(raw)!=expected_digest:raise PermissionError('Service manifest differs from its enrollment')
        doc=_keys(decode_json(raw,65536),{'format','serviceId','hostIdentityDigest','uid','python','package','stores'})
        if doc['format']!='hosting-discovery-service-enrollment/1' or not _id(doc['serviceId']):
            raise ValueError('Unsupported service enrollment manifest')
        result=cls(path,expected_digest,_json(doc));result.require_current();return result

    @property
    def document(self):return decode_json(self.document_json.encode('ascii'),65536)

    def require_current(self):
        if _digest(read_protected(self.path,65536))!=self.digest:
            raise PermissionError('Service enrollment manifest changed')
        doc=self.document
        if not isinstance(doc['stores'],list) or not 1<=len(doc['stores'])<=16:
            raise ValueError('Invalid enrolled retained stores')
        stores={item['name']:item['path'] for item in doc['stores']}
        if len(stores)!=len(doc['stores']):raise ValueError('Ambiguous retained store enrollment')
        if capture_service_facts(doc['serviceId'],stores)!=doc:
            raise PermissionError('Installed service, host, interpreter or retained store identity changed')

    def require_store(self,name,path):
        if not any(item['name']==name and item['path']==str(path) for item in self.document['stores']):
            raise PermissionError('Selected retained store is not enrolled')
