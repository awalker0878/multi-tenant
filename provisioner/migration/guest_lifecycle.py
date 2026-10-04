"""Fixed filesystem and namespace actions for one enrolled Linux application.

The SSH command owner dispatches this installed module with a sealed selection.
It contains no shell, application supplied command, native credential or nested
process launcher. Systemd and mount commands are dispatched separately through
the current per-command worker authority. These observations describe real
kernel/filesystem state; they do not issue migration or recovery permission.
"""
from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import stat
import time
from uuid import UUID

from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import digest, encoded, require, utcnow

FORMAT = 'hosting-application-guest-action/1'
MAX_FILES = 10000
MAX_OUTPUT = 16 * 1024 * 1024
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}')
_HASH = re.compile(r'[0-9a-f]{64}')
ACTION_SOURCE_FILES = frozenset({'provisioner/__init__.py', 'provisioner/domain/__init__.py',
    'provisioner/domain/errors.py', 'provisioner/execution/__init__.py',
    'provisioner/execution/neutron_observe.py', 'provisioner/execution/run_files.py',
    'provisioner/execution/restic_run.py', 'provisioner/migration/resources.py',
    'provisioner/migration/__init__.py', 'provisioner/migration/guest_lifecycle.py'})


def path(value):
    require(isinstance(value, str) and value.startswith('/') and value != '/'
            and re.fullmatch(r'/[A-Za-z0-9_./-]+', value)
            and '..' not in Path(value).parts and str(Path(value)) == value,
            'An exact canonical application path is required')
    selected = Path(value)
    for parent in reversed((selected, *selected.parents)):
        if parent.exists():
            require(not parent.is_symlink() and parent.is_dir(),
                    'An application path or parent was replaced')
    return selected


def _ordinary_tree(root, max_bytes, *, allow_empty=False):
    root = path(str(root))
    require(root.is_dir() and type(max_bytes) is int and 0 < max_bytes <= 2**40,
            'A bounded real application tree is required')
    device = root.stat().st_dev
    files, directories, useful = {}, {}, 0
    for selected in sorted(root.rglob('*')):
        info = selected.lstat()
        require(info.st_dev == device and not stat.S_ISLNK(info.st_mode)
                and (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode))
                and len(files) + len(directories) < MAX_FILES,
                'Application data contains a link, special file or nested filesystem')
        relative = selected.relative_to(root).as_posix()
        metadata = dict(mode=stat.S_IMODE(info.st_mode), uid=info.st_uid, gid=info.st_gid)
        require(metadata['mode'] & 0o7000 == 0, 'Application data has privileged mode bits')
        if stat.S_ISDIR(info.st_mode):
            directories[relative] = metadata
            continue
        require(info.st_nlink == 1 and info.st_size <= max_bytes - useful,
                'Application data has aliased files or exceeds the selected byte budget')
        hasher = hashlib.sha256()
        descriptor = os.open(selected, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            before = os.fstat(descriptor)
            require((before.st_dev, before.st_ino, before.st_size) ==
                    (info.st_dev, info.st_ino, info.st_size), 'Application data changed before capture')
            with os.fdopen(descriptor, 'rb', closefd=False) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    hasher.update(block)
            after = os.fstat(descriptor)
            require((before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                    (after.st_size, after.st_mtime_ns, after.st_ctime_ns),
                    'Application data changed during capture')
        finally:
            os.close(descriptor)
        files[relative] = dict(size=info.st_size, sha256=hasher.hexdigest(), **metadata)
        useful += info.st_size
    require(allow_empty or (files and useful > 0), 'A useful nonempty application dataset is required')
    return dict(files=files, directories=directories, useful_bytes=useful)


def tree(root, max_bytes, *, allow_empty=False):
    before = _ordinary_tree(root, max_bytes, allow_empty=allow_empty)
    require(before == _ordinary_tree(root, max_bytes, allow_empty=allow_empty), 'Application data is not stable')
    return before


def _mount(guest):
    root = path(guest['mount_path'])
    rows = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        fields = line.split()
        separator = fields.index('-')
        require(not any('\\' in value for value in fields[3:6]), 'Escaped application mounts are unsupported')
        if fields[4] == str(root):
            rows.append(dict(device=fields[2], mount_options=fields[5].split(','),
                             fs_type=fields[separator + 1], source=fields[separator + 2],
                             super_options=fields[separator + 3].split(',')))
    require(len(rows) == 1 and rows[0]['fs_type'] == 'ext4', 'One explicit ext4 application mount is required')
    native = root.stat().st_dev
    require(rows[0]['device'] == f'{os.major(native)}:{os.minor(native)}', 'Application mount device changed')
    require(native != Path('/').stat().st_dev, 'The application dataset cannot share its source boot filesystem')
    device = Path('/dev/disk/by-uuid') / guest['filesystem_uuid']
    require(device.is_symlink(), 'The enrolled application filesystem UUID is unavailable')
    info = device.resolve(strict=True).stat()
    require(stat.S_ISBLK(info.st_mode) and info.st_rdev == native,
            'The application mount does not use the enrolled filesystem UUID')
    sys_device = Path('/sys/dev/block', rows[0]['device']).resolve(strict=True)
    if (sys_device / 'partition').exists():
        sys_device = sys_device.parent
    serials = [selected for selected in (sys_device / 'device/wwid', sys_device / 'device/serial') if selected.is_file()]
    require(serials, 'The actual source data disk exposes no independent native serial')
    observed = []
    for selected in serials:
        value = selected.read_text().strip().lower()
        if value.startswith('naa.'):
            value = value[4:]
        observed.append(re.sub('[^0-9a-f]', '', value))
    require(guest['block_serial'] in observed, 'The application filesystem uses another native data disk')
    rows[0]['native_disk_serial'] = guest['block_serial']
    require(path(guest['data_path']).is_relative_to(root), 'Application data escaped its enrolled mount')
    return rows[0]


def _identity(guest):
    require(os.getuid() == os.geteuid() == 0, 'Application filesystem actions require the enrolled root owner')
    release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    require((release.get('ID', '').strip('"'), release.get('VERSION_ID', '').strip('"')) == ('ubuntu', '24.04')
            and Path('/etc/machine-id').read_text().strip() == guest['machine_id']
            and UUID(Path('/sys/class/dmi/id/product_uuid').read_text().strip()) == UUID(guest['native_uuid']),
            'The application action reached another native guest or unsupported image')
    return dict(machine_id=guest['machine_id'], native_uuid=guest['native_uuid'], image='ubuntu-24.04')


def _image(guest):
    executable = Path(guest['executable']['path'])
    unit = Path('/usr/lib/systemd/system') / guest['unit']
    for selected, expected in ((executable, guest['executable']['sha256']), (unit, guest['unit_sha256'])):
        require(selected.is_file() and not selected.is_symlink() and selected.stat().st_uid == 0
                and stat.S_IMODE(selected.stat().st_mode) & 0o022 == 0
                and digest(selected.read_bytes()) == expected,
                'The enrolled application image or immutable vendor unit changed')
    return dict(executable_sha256=guest['executable']['sha256'], unit_sha256=guest['unit_sha256'])


def _fstab(guest, *, writable, expected_sha256):
    selected = Path('/etc/fstab')
    require(not selected.is_symlink() and selected.stat().st_uid == 0
            and stat.S_IMODE(selected.stat().st_mode) & 0o022 == 0,
            'The system mount table is not protected')
    original = selected.read_bytes()
    require(digest(original) == expected_sha256, 'The system mount table changed')
    replacement, count = [], 0
    for line in original.decode('utf-8').splitlines(keepends=True):
        fields = line.split()
        if not fields or fields[0].startswith('#') or len(fields) != 6:
            replacement.append(line)
            continue
        if fields[1] == guest['mount_path']:
            require(fields[0] == 'UUID=' + guest['filesystem_uuid'] and fields[2] == 'ext4',
                    'The persistent application mount differs from its enrollment')
            options = fields[3].split(',')
            require(not set(options) & {'bind', 'rbind', 'x-systemd.automount'},
                    'Aliased or deferred application mounts are unsupported')
            options = [value for value in options if value not in {'ro', 'rw'}]
            fields[3] = ','.join([*options, 'rw' if writable else 'ro'])
            replacement.append('\t'.join(fields) + '\n')
            count += 1
        else:
            replacement.append(line)
    require(count == 1, 'The persistent application mount is missing or duplicated')
    raw = ''.join(replacement).encode()
    temporary = selected.parent / ('.hosting-fstab-' + digest(raw))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.chmod(temporary, stat.S_IMODE(selected.stat().st_mode))
        require(selected.read_bytes() == original, 'The persistent mount table changed before replacement')
        os.replace(temporary, selected)
        directory = os.open(selected.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()
    return dict(before_sha256=digest(original), after_sha256=digest(raw),
                filesystem_uuid=guest['filesystem_uuid'], mount_path=guest['mount_path'],
                selected_option='rw' if writable else 'ro')


def _copy(source, destination, expected, max_bytes):
    source, destination = path(source), path(destination)
    require(not source.is_relative_to(destination) and not destination.is_relative_to(source)
            and not destination.exists(), 'Application copies need distinct new trees')
    require(tree(source, max_bytes) == expected, 'The selected restored dataset changed')
    capacity = os.statvfs(destination.parent)
    require(capacity.f_bavail * capacity.f_frsize >= expected['useful_bytes'],
            'The isolated application copy exceeds available reserved space')
    destination.mkdir(mode=0o700)
    # A crash deliberately leaves the incomplete named tree in place. A later
    # command cannot silently delete it and retry over an uncertain outcome.
    for relative, metadata in expected['directories'].items():
        target = destination / relative
        target.mkdir(mode=0o700)
        os.chown(target, metadata['uid'], metadata['gid'], follow_symlinks=False)
        target.chmod(metadata['mode'])
    for relative, metadata in expected['files'].items():
        selected, target = source / relative, destination / relative
        incoming = os.open(selected, os.O_RDONLY | os.O_NOFOLLOW)
        outgoing = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(incoming, 'rb', closefd=False) as src, os.fdopen(outgoing, 'wb', closefd=False) as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
                dst.flush(); os.fsync(outgoing)
            os.fchown(outgoing, metadata['uid'], metadata['gid'])
            os.fchmod(outgoing, metadata['mode'])
        finally:
            os.close(incoming); os.close(outgoing)
    require(tree(source, max_bytes) == expected and tree(destination, max_bytes) == expected,
            'The application copy did not preserve useful bytes and metadata')
    return dict(source_sha256=digest(encoded(expected)), destination_sha256=digest(encoded(expected)),
                useful_bytes=expected['useful_bytes'])


def _operation(packet, *, new=False):
    from provisioner.execution.run_files import private_path, sync_directory
    base = Path('/var/lib/hosting-application')
    for selected in (base, base / packet['job_id']):
        try:
            selected.mkdir(mode=0o700)
            sync_directory(selected.parent)
        except FileExistsError:
            private_path(selected, directory=True)
    selected = base / packet['job_id'] / packet['operation_id']
    if new:
        selected.mkdir(mode=0o700)
        sync_directory(selected.parent)
    return private_path(selected, directory=True)


def _capture(action, packet, guest, parameters):
    from provisioner.execution import restic_run
    from provisioner.execution.run_files import load_private, write_new
    from provisioner.migration.resources import LinuxApplicationIO
    require({'config', 'max_bytes', 'source_io'} <= parameters.keys(),
            'Final capture needs its exact selected export and finite kernel source-I/O limits')
    config = parameters['config']
    restic_run.validate(config)
    require(config['source'] == guest['data_path'] and config['machine_id'] == guest['machine_id'],
            'The final export changed its original application data or guest')
    controls = LinuxApplicationIO(**parameters['source_io'])
    controls.enter_current(config['source'])
    fenced = _mount(guest)
    require('ro' in fenced['mount_options'] and os.statvfs(guest['mount_path']).f_flag & os.ST_RDONLY,
            'Final capture requires the actual fenced read-only filesystem')
    if action == 'CAPTURE_PREPARE':
        require(set(parameters) == {'config', 'max_bytes', 'source_io'}, 'Exact final capture preparation required')
        before = tree(config['source'], parameters['max_bytes'])
        operation = _operation(packet, new=True)
        payload = restic_run.prepare_capture(config, operation)
        require(payload['files'] == {name: {key: row[key] for key in ('size', 'sha256')}
                for name, row in before['files'].items()}, 'The final export changed while retaining its manifest')
        write_new(operation / 'application-data.json', encoded(before))
        return dict(file_manifest=payload, data=before, source_io=controls.binding())
    operation = _operation(packet)
    payload = load_private(operation / 'manifest.json')
    if action == 'CAPTURE_COMMAND':
        require(set(parameters) == {'config', 'max_bytes', 'source_io', 'stage', 'credentials'}
                and parameters['stage'] in {'REPOSITORY', 'BACKUP'}, 'One exact final repository command required')
        stage = parameters['stage']
        native = operation / ('native-' + stage)
        native.mkdir(mode=0o700)
        client = restic_run.Restic('/usr/bin/restic', config, parameters['credentials'], native,
                                  upload_kib_per_second=controls.bandwidth_kib_per_second)
        if stage == 'REPOSITORY':
            client.repository()
            raw = '{}'
        else:
            argv = restic_run.capture_arguments(config, payload, operation)
            # The source cgroup bounds block reads and restic bounds the actual
            # TLS repository upload, including file data read from cache.
            raw = client.command(argv)
        controls.require_current(config['source'])
        return dict(stage=stage, stdout=raw, source_io=controls.binding())
    require(action == 'CAPTURE_FINISH' and set(parameters) == {'config', 'max_bytes', 'source_io'},
            'Exact original final capture completion required')
    output = (operation / 'native-BACKUP' / '01.json').read_text()
    receipt, manifest = restic_run.finish_capture(config, payload, output, operation)
    before = load_private(operation / 'application-data.json')
    require(tree(config['source'], parameters['max_bytes']) == before,
            'The fenced application bytes or selected metadata changed during final capture')
    controls.require_current(config['source'])
    return dict(source_receipt=receipt, file_manifest=manifest, data=before, source_io=controls.binding())


def _restore(action, packet, guest, parameters):
    from provisioner.execution import restic_run
    from provisioner.execution.run_files import load_private, write_new
    from provisioner.migration.resources import LinuxTransferResources, TransferLimits
    require({'config', 'receipt', 'file_manifest', 'target', 'resources', 'max_bytes'} <= parameters.keys(),
            'An exact independently fenced capture and reserved final restore are required')
    config, receipt, expected, target = (parameters[key] for key in ('config', 'receipt', 'file_manifest', 'target'))
    binding = parameters['resources']
    controls = LinuxTransferResources(Path(binding['stage_parent']), binding['cgroup'], binding['block_device'],
                                      TransferLimits(**binding['limits']))
    controls.enter_current()
    forward = action in {'FORWARD_RESTORE_PREPARE', 'FORWARD_RESTORE_COMMAND', 'FORWARD_RESTORE_FINISH'}
    require((config['machine_id'] == guest['machine_id'] if forward else config['machine_id'] != guest['machine_id'])
            and Path(target).parent == controls.stage_parent
            and controls.limits.expected_bytes == sum(row['size'] for row in expected['files'].values())
            and controls.limits.expected_bytes <= parameters['max_bytes'],
            'The final restore changed its target or exceeds the approved useful-byte ceiling')
    if action in {'RESTORE_PREPARE', 'FORWARD_RESTORE_PREPARE'}:
        require(set(parameters) == {'config', 'receipt', 'file_manifest', 'target', 'resources', 'max_bytes'},
                'Exact final restore preparation required')
        restic_run.validate_restore_capture(config, receipt, expected, target)
        controls.require_capacity(len(encoded(expected)))
        operation = _operation(packet, new=True)
        write_new(operation / 'restore-inputs.json', encoded(parameters))
        write_new(operation / 'restore-start.json', encoded(dict(monotonic=time.monotonic(),
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())))
        return dict(resource_binding=controls.binding(), source_manifest_sha256=digest(encoded(expected)))
    operation = _operation(packet)
    original = load_private(operation / 'restore-inputs.json')
    require({key: parameters[key] for key in original} == original,
            'The originally retained final restore changed')
    if action in {'RESTORE_COMMAND', 'FORWARD_RESTORE_COMMAND'}:
        require(set(parameters) == set(original) | {'stage', 'credentials'}
                and parameters['stage'] in {'REPOSITORY', 'SNAPSHOTS', 'RESTORE'},
                'One exact original final restore command is required')
        stage = parameters['stage']
        native = operation / ('native-' + stage)
        native.mkdir(mode=0o700)
        client = restic_run.Restic('/usr/bin/restic', config, parameters['credentials'], native,
                                    resource_control=controls)
        if stage == 'REPOSITORY':
            client.repository(); raw = '{}'
        elif stage == 'SNAPSHOTS':
            raw = client.command(['snapshots', receipt['snapshot_id']])
        else:
            snapshots = strict_loads((operation / 'native-SNAPSHOTS' / '01.json').read_bytes())
            restic_run.prepare_restore_target(config, receipt, expected, operation, target, snapshots)
            raw = client.command(['restore', receipt['snapshot_id'], '--target', target, '--verify'])
        controls.require_current()
        return dict(stage=stage, stdout=raw, resource_binding=controls.binding())
    require(action in {'RESTORE_FINISH', 'FORWARD_RESTORE_FINISH'} and set(parameters) == set(original),
            'Only the exact original restore can be read back')
    start = load_private(operation / 'restore-start.json')
    started = start['monotonic']
    require(started <= time.monotonic() and start['boot_id'] ==
            Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'The original restore spans an unknown guest restart')
    restored = restic_run.finish_restore(config, receipt, expected, operation, target,
                                        elapsed_seconds=time.monotonic() - started)
    data = tree(str(Path(target) / config['source'].lstrip('/')), parameters['max_bytes'])
    controls.require_current()
    return dict(restore_receipt=restored, data=data, resource_binding=controls.binding())


def _health(guest, pid, *, isolated, isolated_data_path=None):
    require(type(pid) is int and pid > 1, 'The actual application MainPID is required')
    status = Path(f'/proc/{pid}/status').read_text()
    uid = next((line.split()[1:] for line in status.splitlines() if line.startswith('Uid:')), [])
    require(uid == [str(guest['uid'])] * 4, 'The application process does not use its unprivileged enrollment')
    before = os.stat(f'/proc/{pid}/ns/net').st_ino
    controller = os.stat('/proc/self/ns/net').st_ino
    require((before != controller) if isolated else (before == controller),
            'The application network namespace differs from the selected phase')
    if isolated:
        expected = path(isolated_data_path).stat()
        production = path(guest['data_path']).stat()
        observed = Path(f'/proc/{pid}/root{guest["data_path"]}').stat()
        require((observed.st_dev, observed.st_ino) == (expected.st_dev, expected.st_ino)
                and (observed.st_dev, observed.st_ino) != (production.st_dev, production.st_ino)
                and os.stat(f'/proc/{pid}/ns/mnt').st_ino != os.stat('/proc/self/ns/mnt').st_ino,
                'The rehearsal process can see the production dataset instead of its isolated copy')
    # proc namespace handles are kernel magic links, not ordinary selected
    # filesystem paths. Bind the opened handle to the observed namespace inode.
    namespace = os.open(f'/proc/{pid}/ns/net', os.O_RDONLY)
    require(os.fstat(namespace).st_ino == before, 'The application namespace changed before entry')
    try:
        if isolated:
            library = ctypes.CDLL(None, use_errno=True)
            require(library.setns(namespace, 0x40000000) == 0,
                    'The actual isolated application network namespace could not be entered')
        health = guest['health']
        connection = http.client.HTTPConnection('127.0.0.1', health['port'], timeout=3)
        try:
            connection.request('GET', health['path'], headers={'Connection': 'close'})
            response = connection.getresponse()
            body = response.read(1024 * 1024 + 1)
            require(response.status == 200 and len(body) <= 1024 * 1024
                    and digest(body) == health['response_sha256'],
                    'The application useful health response differs')
        finally:
            connection.close()
        require(os.stat(f'/proc/{pid}/ns/net').st_ino == before,
                'The application process changed during its health probe')
        return dict(main_pid=pid, process_uid=guest['uid'], network_namespace_inode=before,
                    controller_namespace_inode=controller, response_sha256=digest(body))
    finally:
        os.close(namespace)


def execute(action, packet):
    require(isinstance(packet, dict) and set(packet) ==
            {'format', 'job_id', 'operation_id', 'selection_sha256', 'guest', 'parameters'}
            and packet['format'] == FORMAT and _ID.fullmatch(packet['job_id'])
            and _ID.fullmatch(packet['operation_id']) and _HASH.fullmatch(packet['selection_sha256']),
            'The exact original guest application action is required')
    guest, parameters = packet['guest'], packet['parameters']
    require(isinstance(guest, dict) and isinstance(parameters, dict)
            and type(guest.get('uid')) is int and 100 <= guest['uid'] <= 60000
            and type(guest.get('gid')) is int and 100 <= guest['gid'] <= 60000,
            'One selected unprivileged Linux application is required')
    identity = _identity(guest)
    if action in {'CAPTURE_PREPARE', 'CAPTURE_COMMAND', 'CAPTURE_FINISH'}:
        result = _capture(action, packet, guest, parameters)
    elif action in {'RESTORE_PREPARE', 'RESTORE_COMMAND', 'RESTORE_FINISH',
                   'FORWARD_RESTORE_PREPARE', 'FORWARD_RESTORE_COMMAND', 'FORWARD_RESTORE_FINISH'}:
        result = _restore(action, packet, guest, parameters)
    elif action == 'IMAGE_OBSERVE':
        require(parameters == {}, 'Image observation takes no action parameters')
        result = _image(guest)
    elif action == 'DATA_OBSERVE':
        require(set(parameters) == {'path', 'max_bytes'}, 'Exact staged application dataset required')
        result = dict(data=tree(parameters['path'], parameters['max_bytes']))
    elif action == 'DATABASE_SEPARATION_OBSERVE':
        require(set(parameters) == {'data_directory'}, 'One exact current native PostgreSQL directory is required')
        database = path(parameters['data_directory'])
        app_mount = _mount(guest)
        require(database.is_dir() and database.stat().st_dev != Path(guest['mount_path']).stat().st_dev,
            'The actual PostgreSQL engine shares the application file disk being fenced')
        result = dict(data_directory=str(database), database_device=f'{os.major(database.stat().st_dev)}:{os.minor(database.stat().st_dev)}',
                      application_device=app_mount['device'])
    elif action in {'REMOUNT_READONLY', 'REMOUNT_READWRITE'}:
        require(parameters == {}, 'The enrolled mount is the only remount target')
        before = _mount(guest)
        library = ctypes.CDLL(None, use_errno=True)
        library.mount.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_ulong, ctypes.c_void_p]
        library.mount.restype = ctypes.c_int
        options = 32 | (1 if action == 'REMOUNT_READONLY' else 0)
        result_code = library.mount(None, guest['mount_path'].encode(), None, options, None)
        require(result_code == 0, 'The exact application filesystem remount did not complete')
        after = _mount(guest)
        require(('ro' if action == 'REMOUNT_READONLY' else 'rw') in after['mount_options'],
                'The application mount postcondition differs')
        result = dict(before=before, after=after)
    elif action in {'OBSERVE', 'TARGET_OBSERVE'}:
        require(set(parameters) == {'max_bytes'}, 'Exact observation budget required')
        result = dict(mount=_mount(guest), data=tree(guest['data_path'], parameters['max_bytes'],
                                                   allow_empty=action == 'TARGET_OBSERVE'),
                      fstab_sha256=digest(Path('/etc/fstab').read_bytes()))
    elif action in {'READONLY_OBSERVE', 'TARGET_READONLY_OBSERVE'}:
        require(set(parameters) == {'max_bytes'}, 'Exact fence observation budget required')
        mount = _mount(guest)
        require('ro' in mount['mount_options'] and 'rw' not in mount['mount_options']
                and os.statvfs(guest['mount_path']).f_flag & os.ST_RDONLY,
                'The actual application filesystem remains writable')
        probe = path(guest['data_path']) / ('.hosting-fence-' + packet['operation_id'])
        try:
            descriptor = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except OSError as error:
            require(error.errno == errno.EROFS, 'The application writer probe did not encounter a read-only filesystem')
        else:
            os.close(descriptor)
            raise ValueError('The application filesystem admitted a writer')
        result = dict(mount=mount, data=tree(guest['data_path'], parameters['max_bytes'],
                                            allow_empty=action == 'TARGET_READONLY_OBSERVE'),
                      fstab_sha256=digest(Path('/etc/fstab').read_bytes()), write_errno=errno.EROFS)
    elif action in {'BOOT_READONLY', 'BOOT_READWRITE'}:
        require(set(parameters) == {'fstab_sha256'} and _HASH.fullmatch(parameters['fstab_sha256']),
                'The exact observed persistent mount table is required')
        result = _fstab(guest, writable=action == 'BOOT_READWRITE',
                        expected_sha256=parameters['fstab_sha256'])
    elif action in {'COPY_REHEARSAL', 'COPY_FINAL', 'COPY_RECOVERY'}:
        require(set(parameters) == {'source', 'destination', 'manifest', 'max_bytes'},
                'The exact selected application copy is required')
        result = _copy(parameters['source'], parameters['destination'], parameters['manifest'],
                       parameters['max_bytes'])
        os.chown(parameters['destination'], guest['uid'], guest['gid'], follow_symlinks=False)
        os.chmod(parameters['destination'], 0o750)
    elif action in {'HEALTH_ISOLATED', 'HEALTH_PRODUCTION'}:
        require(set(parameters) == ({'main_pid', 'isolated_data_path'} if action == 'HEALTH_ISOLATED'
                                    else {'main_pid'}), 'The actual observed application process is required')
        result = _health(guest, parameters['main_pid'], isolated=action == 'HEALTH_ISOLATED',
                         isolated_data_path=parameters.get('isolated_data_path'))
    elif action == 'ACTIVATION_MARKER':
        require(set(parameters) == {'final_manifest_sha256', 'original_source_fence_sha256'}
                and all(_HASH.fullmatch(value) for value in parameters.values()),
                'Activation must retain the exact source fence and final data identity')
        selected = _operation(packet, new=True) / 'activation-marker.json'
        marker = {key: packet[key] for key in ('job_id', 'operation_id', 'selection_sha256')}
        marker.update(parameters, at=utcnow().isoformat(), boundary='TARGET_WRITES_POSSIBLE')
        raw = encoded(marker)
        descriptor = os.open(selected, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        parent = os.open(selected.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
        result = dict(marker_sha256=digest(raw), boundary='TARGET_WRITES_POSSIBLE')
    elif action == 'PUBLISH_FINAL':
        require(set(parameters) == {'source', 'manifest', 'max_bytes'},
                'Exact final useful application bytes and metadata are required')
        mount = _mount(guest)
        require('rw' in mount['mount_options'], 'The current admitted target filesystem is not writable')
        operation = _operation(packet)
        from provisioner.execution.run_files import load_private, write_new, sync_directory
        marker = load_private(operation / 'activation-marker.json')
        require(marker['final_manifest_sha256'] == digest(encoded(parameters['manifest'])),
                'The final dataset changed after original target write admission')
        replacement = path(guest['mount_path']) / ('.hosting-publish-' + packet['operation_id'])
        retained = path(guest['mount_path']) / ('.hosting-before-' + packet['operation_id'])
        require(not retained.exists(), 'The original target data directory was already replaced')
        copied = _copy(parameters['source'], str(replacement), parameters['manifest'], parameters['max_bytes'])
        os.chown(replacement, guest['uid'], guest['gid'], follow_symlinks=False); replacement.chmod(0o750)
        write_new(operation / 'publication-attempt.json', encoded(dict(data_path=guest['data_path'],
            replacement=str(replacement), retained=str(retained), manifest_sha256=digest(encoded(parameters['manifest'])))))
        os.rename(path(guest['data_path']), retained)
        os.rename(replacement, guest['data_path'])
        sync_directory(guest['mount_path'])
        require(tree(guest['data_path'], parameters['max_bytes']) == parameters['manifest'],
                'The published target application differs from the final fenced export')
        result = dict(copied=copied, publication_manifest_sha256=digest(encoded(parameters['manifest'])),
                      retained_prior_data=str(retained))
    else:
        raise ValueError('Unimplemented guest application action')
    return dict(format='hosting-application-guest-observation/1', action=action, identity=identity,
                **{key: packet[key] for key in ('job_id', 'operation_id', 'selection_sha256')},
                observed_at=utcnow().isoformat(), observation=result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', required=True)
    arguments = parser.parse_args()
    try:
        import sys
        raw = sys.stdin.buffer.read(MAX_OUTPUT + 1)
        require(len(raw) <= MAX_OUTPUT, 'Guest application action input exceeds its bound')
        result = execute(arguments.action, strict_loads(raw))
        print(json.dumps(result, sort_keys=True, separators=(',', ':')))
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        print('{"status":"APPLICATION_GUEST_ACTION_HELD"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
