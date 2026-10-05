"""Private single-node development dependencies and explicitly scoped probe identities."""
from __future__ import annotations
import base64
import hashlib
import json
from pathlib import Path
import re
import secrets
import subprocess
import time

from local_runtime import _base, _bind, _openssl, _secret, _write


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def b64(value):
    return base64.urlsafe_b64encode(value).decode().rstrip('=')


def prepare(root: Path, directory: Path, images: dict):
    if any(not re.fullmatch(r'(?:[a-z0-9./_-]+@)?sha256:[0-9a-f]{64}', image) for image in images.values()):
        raise ValueError('Every image must be immutable')
    directory.mkdir(mode=0o700, exist_ok=False)
    private = directory/'secrets'; private.mkdir(mode=0o700)
    config = directory/'config'; config.mkdir(mode=0o755)
    passwords = ['postgres-password', 'temporal-runtime-password', 'visibility-runtime-password', 'temporal-migrator-password', 'visibility-migrator-password', 'publisher-password', 'consumer-password', 'foreign-broker-password']
    passwords += [prefix+name+'-password' for prefix in ('', 'restore-') for name in ('root', 'assurance', 'foreign')]
    for name in passwords:
        _write(private/name, secrets.token_urlsafe(32)+'\n')
    _openssl('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(private/'ca.key'), '-out', str(private/'ca.crt'), '-days', '2', '-sha256', '-subj', '/CN=P01 stateful fixture CA', '-addext', 'basicConstraints=critical,CA:TRUE', '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
    (private/'ca.key').chmod(0o400); (private/'ca.crt').chmod(0o444)
    for name in ('rabbit', 'temporal', 'postgres', 'evidence', 'evidence-restore'):
        _write(private/(name+'.ext'), 'basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:'+name+'\n')
        _openssl('req', '-new', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(private/(name+'.key')), '-out', str(private/(name+'.csr')), '-subj', '/CN='+name)
        _openssl('x509', '-req', '-in', str(private/(name+'.csr')), '-CA', str(private/'ca.crt'), '-CAkey', str(private/'ca.key'), '-set_serial', str(secrets.randbits(128)+1), '-days', '2', '-sha256', '-extfile', str(private/(name+'.ext')), '-out', str(private/(name+'.crt')))
        for suffix in ('key', 'crt'): (private/(name+'.'+suffix)).chmod(0o444)
        for suffix in ('csr', 'ext'): (private/(name+'.'+suffix)).unlink()
    # The issuer signing key stays outside every container and every evidence bundle.
    _openssl('genpkey', '-algorithm', 'RSA', '-pkeyopt', 'rsa_keygen_bits:2048', '-out', str(private/'issuer.key'))
    (private/'issuer.key').chmod(0o400)
    modulus = subprocess.run(['openssl', 'rsa', '-in', str(private/'issuer.key'), '-noout', '-modulus'], capture_output=True, check=True).stdout.decode().strip().split('=', 1)[1]
    jwks = {'keys': [{'kty': 'RSA', 'kid': 'fixture', 'use': 'sig', 'alg': 'RS256', 'n': b64(bytes.fromhex(modulus)), 'e': 'AQAB'}]}
    _write(config/'jwks.json', json.dumps(jwks)+'\n')
    now = int(time.time())
    token_specs = {'admin': ['temporal-system:admin'], 'lifecycle': ['lifecycle:read', 'lifecycle:write', 'lifecycle:worker'], 'foreign': ['inventory:read'], 'expired': ['lifecycle:read'], 'wrong-audience': ['lifecycle:read']}
    for name, permissions in token_specs.items():
        claims = {'sub': name, 'aud': 'p01-temporal' if name != 'wrong-audience' else 'foreign-audience', 'iat': now-120, 'exp': now-60 if name == 'expired' else now+7200, 'permissions': permissions}
        payload = b64(encode({'alg': 'RS256', 'kid': 'fixture', 'typ': 'JWT'}))+'.'+b64(encode(claims))
        signature = subprocess.run(['openssl', 'dgst', '-sha256', '-sign', str(private/'issuer.key')], input=payload.encode(), capture_output=True, check=True).stdout
        _write(private/('jwt-'+name), payload+'.'+b64(signature)+'\n')
    users = []
    for name, secret in [('publisher', 'publisher-password'), ('consumer', 'consumer-password'), ('foreign', 'foreign-broker-password')]:
        salt = secrets.token_bytes(4)
        users.append({'name': name, 'password_hash': base64.b64encode(salt+hashlib.sha256(salt+(private/secret).read_text().strip().encode()).digest()).decode(), 'hashing_algorithm': 'rabbit_password_hashing_sha256', 'tags': []})
    definitions = {'users': users, 'vhosts': [{'name': 'p01'}, {'name': 'foreign'}], 'permissions': [
        {'user': 'publisher', 'vhost': 'p01', 'configure': '^$', 'write': '^events$', 'read': '^$'},
        {'user': 'consumer', 'vhost': 'p01', 'configure': '^$', 'write': '^$', 'read': '^deliveries$'},
        {'user': 'foreign', 'vhost': 'foreign', 'configure': '^$', 'write': '^$', 'read': '^$'}],
        'exchanges': [{'name': 'events', 'vhost': 'p01', 'type': 'direct', 'durable': True, 'auto_delete': False, 'internal': False, 'arguments': {}}],
        'queues': [{'name': 'deliveries', 'vhost': 'p01', 'durable': True, 'auto_delete': False, 'arguments': {}}],
        'bindings': [{'source': 'events', 'vhost': 'p01', 'destination': 'deliveries', 'destination_type': 'queue', 'routing_key': 'witness', 'arguments': {}}]}
    _write(config/'definitions.json', json.dumps(definitions))
    _write(config/'rabbitmq.conf', '''listeners.tcp = none
listeners.ssl.default = 5671
ssl_options.cacertfile = /run/secrets/ca.crt
ssl_options.certfile = /run/secrets/rabbit.crt
ssl_options.keyfile = /run/secrets/rabbit.key
ssl_options.verify = verify_none
ssl_options.fail_if_no_peer_cert = false
management.tcp.ip = 127.0.0.1
prometheus.tcp.ip = 127.0.0.1
definitions.import_backend = local_filesystem
definitions.local.path = /run/config/definitions.json
''')
    stores = {}
    for name, db in [('temporal', 'temporal'), ('visibility', 'temporal_visibility')]:
        stores[name] = {'sql': {'pluginName': 'postgres12', 'databaseName': db, 'connectAddr': 'postgres:5432', 'connectProtocol': 'tcp', 'user': name+'_runtime', 'password': (private/(name+'-runtime-password')).read_text().strip(), 'maxConns': 5, 'maxIdleConns': 5, 'maxConnLifetime': '1h', 'tls': {'enabled': True, 'caFile': '/run/secrets/ca.crt', 'enableHostVerification': True, 'serverName': 'postgres'}}}
    temporal = {'log': {'stdout': True, 'level': 'warn'}, 'persistence': {'defaultStore': 'temporal', 'visibilityStore': 'visibility', 'numHistoryShards': 4, 'datastores': stores},
        'global': {'membership': {'maxJoinDuration': '30s', 'broadcastAddress': '127.0.0.1'}, 'tls': {'frontend': {'server': {'certFile': '/run/secrets/temporal.crt', 'keyFile': '/run/secrets/temporal.key', 'requireClientAuth': False}}}, 'authorization': {'authorizer': 'default', 'claimMapper': 'default', 'audience': 'p01-temporal', 'jwtKeyProvider': {'keySourceURIs': ['file:///run/config/jwks.json'], 'refreshInterval': '1s'}}},
        'services': {name: {'rpc': {'grpcPort': port, 'membershipPort': port-300, **({'bindOnIP': '0.0.0.0'} if name == 'frontend' else {'bindOnLocalHost': True})}} for name, port in [('frontend', 7233), ('history', 7234), ('matching', 7235), ('internal-frontend', 7236), ('worker', 7239)]},
        'clusterMetadata': {'enableGlobalNamespace': False, 'failoverVersionIncrement': 10, 'masterClusterName': 'active', 'currentClusterName': 'active', 'clusterInformation': {'active': {'enabled': True, 'initialFailoverVersion': 1, 'rpcName': 'frontend', 'rpcAddress': '127.0.0.1:7233'}}},
        'dynamicConfigClient': {'filepath': '/run/config/dynamic.yaml', 'pollInterval': '1s'}}
    _write(private/'temporal.yaml', json.dumps(temporal))
    _write(config/'dynamic.yaml', 'system.enableInternalFrontend:\n  - value: true\n')
    for name, prefix in [('assurance', 't_demo'), ('foreign', 't_other')]:
        policy = {'Version': '2012-10-17', 'Statement': [{'Effect': 'Allow', 'Action': ['s3:GetObject', 's3:GetObjectVersion', 's3:GetObjectRetention', 's3:PutObject'], 'Resource': ['arn:aws:s3:::p01-evidence/'+prefix+'/*']}]}
        _write(config/(name+'-policy.json'), json.dumps(policy))
    fixture = root/'deploy/fixtures/stateful'
    services = {}
    def service(image, networks, secret_names=(), **extra):
        return {**_base(image), 'networks': networks, 'user': '10001:10001', 'tmpfs': ['/tmp:mode=1777'], 'mem_limit': '512m', 'pids_limit': 256, 'secrets': [_secret(n) for n in secret_names], **extra}
    services['rabbit'] = service(images['rabbitmq'], ['broker'], ['ca.crt', 'rabbit.crt', 'rabbit.key'], user='999:999', hostname='rabbit', mem_limit='768m', environment={'RABBITMQ_NODENAME': 'rabbit@rabbit', 'RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS': '+S 2:2', 'RABBITMQ_CTL_ERL_ARGS': '+S 2:2'}, volumes=['broker:/var/lib/rabbitmq', _bind(config/'rabbitmq.conf', '/etc/rabbitmq/rabbitmq.conf'), _bind(config/'definitions.json', '/run/config/definitions.json')], healthcheck={'test': ['CMD-SHELL', 'rabbitmq-diagnostics -q check_running && rabbitmq-diagnostics -q check_port_connectivity --address 127.0.0.1'], 'interval': '3s', 'timeout': '5s', 'retries': 50})
    services['postgres'] = service(images['postgres'], ['database'], ['ca.crt', 'postgres.crt', 'postgres.key', 'postgres-password', 'temporal-runtime-password', 'visibility-runtime-password', 'temporal-migrator-password', 'visibility-migrator-password'], user='0:0', cap_add=['CHOWN', 'DAC_OVERRIDE', 'FOWNER', 'SETGID', 'SETUID'], entrypoint=['bash', '/fixture/postgres.sh'], tmpfs=['/tmp:mode=1777', '/var/run/postgresql:mode=1777'], volumes=['database:/var/lib/postgresql', _bind(fixture/'postgres.sh', '/fixture/postgres.sh'), _bind(fixture/'initialize.sh', '/docker-entrypoint-initdb.d/10-stateful.sh')], healthcheck={'test': ['CMD-SHELL', 'pg_isready -h /var/run/postgresql -U postgres -d postgres'], 'interval': '1s', 'timeout': '3s', 'retries': 90})
    services['schema'] = service(images['temporal_admin'], ['database'], ['ca.crt', 'temporal-migrator-password', 'visibility-migrator-password'], entrypoint=['sh', '/fixture/schema.sh'], volumes=[_bind(fixture/'schema.sh', '/fixture/schema.sh')], profiles=['administration'])
    services['temporal'] = service(images['temporal'], ['workflow', 'database'], ['ca.crt', 'temporal.crt', 'temporal.key', 'temporal.yaml'], user='1000:1000', mem_limit='1g', entrypoint=['temporal-server', '--config-file', '/run/secrets/temporal.yaml', 'start', '--service', 'frontend', '--service', 'history', '--service', 'matching', '--service', 'internal-frontend', '--service', 'worker'], volumes=[_bind(config/'jwks.json', '/run/config/jwks.json'), _bind(config/'dynamic.yaml', '/run/config/dynamic.yaml')])
    def probe(name, network, secrets_, **extra):
        services[name] = service(images['probe'], [network], ['ca.crt', *secrets_], profiles=['probe'], **extra)
    probe('broker-client', 'broker', ['publisher-password', 'consumer-password', 'foreign-broker-password'])
    probe('workflow-client', 'workflow', ['jwt-lifecycle', 'jwt-foreign', 'jwt-expired', 'jwt-wrong-audience'])
    probe('workflow-admin', 'workflow', ['jwt-admin'])
    probe('database-client', 'database', ['temporal-runtime-password', 'visibility-runtime-password'])
    for prefix, server in [('', 'evidence'), ('restore-', 'evidence-restore')]:
        network = server
        services[server] = service(images['minio'], [network], [], entrypoint=['sh', '-ec', 'export MINIO_ROOT_USER=p01root MINIO_ROOT_PASSWORD="$(cat /run/secrets/root-password)" MINIO_BROWSER=off; exec minio server --quiet --address :9000 --certs-dir /certs /data'], secrets=[_secret(prefix+'root-password', 'root-password')], volumes=[server+':/data', _bind(private/(server+'.crt'), '/certs/public.crt'), _bind(private/(server+'.key'), '/certs/private.key')])
        env = {'S3_ENDPOINT': 'https://'+server+':9000'}
        probe(prefix+'evidence-client', network, [], environment=env, secrets=[_secret('ca.crt'), _secret(prefix+'assurance-password', 'assurance-password'), _secret(prefix+'foreign-password', 'foreign-password')])
        probe(prefix+'evidence-admin', network, [], environment=env, secrets=[_secret('ca.crt'), _secret(prefix+'root-password', 'root-password')])
        services[prefix+'evidence-iam'] = service(images['mc'], [network], [], entrypoint=['sh', '/fixture/mc.sh'], environment=env, profiles=['administration'], secrets=[_secret('ca.crt'), *[_secret(prefix+n+'-password', n+'-password') for n in ('root', 'assurance', 'foreign')]], volumes=[_bind(fixture/'mc.sh', '/fixture/mc.sh'), *[_bind(config/(n+'-policy.json'), '/fixture/'+n+'-policy.json') for n in ('assurance', 'foreign')]])
    compose = {'name': 'p01-stateful-'+secrets.token_hex(6), 'services': services, 'networks': {n: {'internal': True} for n in ('broker', 'workflow', 'database', 'evidence', 'evidence-restore')}, 'volumes': {n: {} for n in ('broker', 'database', 'evidence', 'evidence-restore')}, 'secrets': {p.name: {'file': str(p)} for p in private.iterdir() if p.is_file() and p.name not in ('ca.key', 'issuer.key')}}
    path = directory/'compose.json'; _write(path, json.dumps(compose, indent=2))
    return path
