"""Derive a two-owner messaging topology from the tested private PostgreSQL installer."""
import base64
import hashlib
import json
from pathlib import Path
import secrets

from local_runtime import SERVICES, _base, _bind, _openssl, _secret, _write, prepare as base_prepare


def prepare(root, runtime, images, revision):
    # Unused application declarations are removed before any container is started.
    path=base_prepare(root,runtime,{name:images.get(name,images['planning']) for name in SERVICES},revision)
    d=json.loads(path.read_text());private=runtime/'secrets'
    for name in ('catalogue','planning'):
        _write(private/(name+'-broker-password'),secrets.token_urlsafe(32)+'\n')
        d['secrets'][name+'-broker-password']={'file':str(private/(name+'-broker-password'))}
    _write(private/'rabbit.ext','basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:rabbit\n')
    _openssl('req','-new','-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256','-nodes','-keyout',str(private/'rabbit.key'),'-out',str(private/'rabbit.csr'),'-subj','/CN=rabbit')
    _openssl('x509','-req','-in',str(private/'rabbit.csr'),'-CA',str(private/'ca.crt'),'-CAkey',str(private/'ca.key'),'-set_serial',str(secrets.randbits(128)+1),'-days','2','-sha256','-extfile',str(private/'rabbit.ext'),'-out',str(private/'rabbit.crt'))
    for suffix in ('key','crt'):
        (private/('rabbit.'+suffix)).chmod(0o444);d['secrets']['rabbit.'+suffix]={'file':str(private/('rabbit.'+suffix))}
    users=[]
    for name in ('catalogue','planning'):
        salt=secrets.token_bytes(4);password=(private/(name+'-broker-password')).read_text().strip()
        users.append({'name':name,'password_hash':base64.b64encode(salt+hashlib.sha256(salt+password.encode()).digest()).decode(),'hashing_algorithm':'rabbit_password_hashing_sha256','tags':[]})
    definitions={'users':users,'vhosts':[{'name':'product'}],'permissions':[
        {'user':'catalogue','vhost':'product','configure':'^$','write':'^catalogue.events$','read':'^$'},
        {'user':'planning','vhost':'product','configure':'^$','write':'^$','read':'^planning.(facts|quarantine)$'}],
        'exchanges':[{'name':n,'vhost':'product','type':'direct','durable':True,'auto_delete':False,'internal':False,'arguments':{}} for n in ('catalogue.events','planning.dead')],
        'queues':[{'name':n,'vhost':'product','durable':True,'auto_delete':False,'arguments':args} for n,args in [('planning.facts',{'x-queue-type':'quorum','x-delivery-limit':5,'x-dead-letter-exchange':'planning.dead','x-dead-letter-routing-key':'rejected'}),('planning.quarantine',{'x-queue-type':'quorum'})]],
        'bindings':[{'source':ex,'vhost':'product','destination':q,'destination_type':'queue','routing_key':key,'arguments':{}} for ex,q,key in [('catalogue.events','planning.facts','catalogue.foundation.recorded.v1'),('planning.dead','planning.quarantine','rejected')]]}
    _write(runtime/'definitions.json',json.dumps(definitions))
    _write(runtime/'rabbitmq.conf','listeners.tcp = none\nlisteners.ssl.default = 5671\nssl_options.cacertfile = /run/secrets/ca.crt\nssl_options.certfile = /run/secrets/rabbit.crt\nssl_options.keyfile = /run/secrets/rabbit.key\nssl_options.verify = verify_none\nssl_options.fail_if_no_peer_cert = false\nmanagement.tcp.ip = 127.0.0.1\nprometheus.tcp.ip = 127.0.0.1\ndefinitions.import_backend = local_filesystem\ndefinitions.skip_if_unchanged = true\ndefinitions.local.path = /run/config/definitions.json\n')
    kept={'postgres':d['services']['postgres']}
    kept['postgres']['networks']=['db_catalogue','db_planning']
    for name,language in [('catalogue','php'),('planning','python')]:
        service=d['services'][name]
        service.update(networks=['db_'+name,'broker'],depends_on={},entrypoint=['php','/probe/producer.php'] if language=='php' else ['/opt/venv/bin/python','/probe/consumer.py'],command=[],volumes=[_bind(root/'scripts/p01/messaging','/probe')],profiles=['probe'])
        service['secrets'].append(_secret(name+'-broker-password','broker-password'))
        kept[name]=service
    kept['rabbit']={**_base(images['rabbit']),'user':'999:999','hostname':'rabbit','networks':['broker'],'mem_limit':'768m','tmpfs':['/tmp:mode=1777'],'volumes':['broker_data:/var/lib/rabbitmq',_bind(runtime/'rabbitmq.conf','/etc/rabbitmq/rabbitmq.conf'),_bind(runtime/'definitions.json','/run/config/definitions.json')],'environment':{'RABBITMQ_NODENAME':'rabbit@rabbit','RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS':'+S 2:2','RABBITMQ_CTL_ERL_ARGS':'+S 2:2'},'secrets':[_secret(n) for n in ('ca.crt','rabbit.key','rabbit.crt')],'healthcheck':{'test':['CMD-SHELL','rabbitmq-diagnostics -q check_running && rabbitmq-diagnostics -q check_port_connectivity --address 127.0.0.1'],'interval':'3s','timeout':'5s','retries':50}}
    d.update(services=kept,networks={n:{'internal':True} for n in ('db_catalogue','db_planning','broker')});d['volumes']['broker_data']={}
    _write(path,json.dumps(d,indent=2),0o600)
    return path
