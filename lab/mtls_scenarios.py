"""Executed after the original 33 packet assertions on the same permitted path."""
import ipaddress
from pathlib import Path
import tempfile
from mtls_fixture import material


def exercise(workers,data,record):
    address=next(str(ipaddress.ip_interface(i['address']).ip) for i in data['nodes']['data-01']['interfaces'] if ipaddress.ip_interface(i['address']).version==4)
    with tempfile.TemporaryDirectory(prefix='hosting-mtls-') as tmp:
        m=material(Path(tmp))
        workers['data-01'].call('mtls-start',address=address,port=443,ca=m['ca'],
                                certificate=m['server']['certificate'],key=m['server']['key'],allowed=[m['client']['fingerprint']])
        def probe(label='client',**kwargs):
            params={} if label is None else {'certificate':m[label]['certificate'],'key':m[label]['key']}
            return workers['processor-01'].call('mtls-probe',address=address,port=443,ca=kwargs.pop('ca',m['ca']),**params,**kwargs)
        p=probe()
        record('mTLS accepted client over the routed OZ-to-RZ path',p['success'] and p.get('tls_version')=='TLSv1.3',p)
        before=workers['data-01'].call('mtls-stats')
        p=probe('other-tenant')
        after=workers['data-01'].call('mtls-stats')
        record('Trusted other-tenant certificate denied by service resource authority on an allowed network path',
               not p['success'] and p.get('observation')=='RESOURCE_DENIED' and after['resource_denied']>before['resource_denied'],
               {'probe':p,'server_before':before,'server_after':after,'test_origin':'processor-01 with tenant-002 test identity'})
        for label,title in [(None,'Missing client certificate'),('expired','Expired client certificate'),('foreign','Untrusted issuer client certificate')]:
            p=probe(label)
            control=probe()
            record(title+' rejected while valid identity still works',not p['success'] and control['success'],{'denied':p,'control':control})
        p=probe(hostname='wrong.fixture.invalid');control=probe()
        record('Incorrect server hostname rejected',not p['success'] and control['success'],{'denied':p,'control':control})
        p=probe(ca=m['other_ca']);control=probe()
        record('Untrusted server root rejected',not p['success'] and control['success'],{'denied':p,'control':control})
        p=workers['processor-01'].call('probe',address=address,port=443)
        control=probe()
        record('No plaintext fallback on the mTLS endpoint',not p['success'] and control['success'],{'plaintext':p,'tls_control':control})
        old=probe(retained='tls-old')
        record('Old credential has an established authorized session before rotation',old['success'],old)
        workers['data-01'].call('mtls-grants',allowed=[m['client']['fingerprint'],m['rotated']['fingerprint']])
        p=probe('rotated',retained='tls-new');old=probe(retained='tls-old')
        record('Bounded credential overlap supports new and existing identities',p['success'] and old['success'],{'new':p,'old':old})
        state=workers['data-01'].call('mtls-grants',allowed=[m['rotated']['fingerprint']])
        old=probe(retained='tls-old');oldnew=probe();new=probe('rotated',retained='tls-new')
        record('Credential withdrawal closes existing old session and denies new use without losing new session',
               not old['success'] and not oldnew['success'] and new['success'] and state['withdrawn_connections']>=1,
               {'old_existing':old,'old_new':oldnew,'new_existing':new,'service':state,'meaning':'Resource grant withdrawal; not a CRL/OCSP claim'})
        workers['data-01'].call('mtls-grants',allowed=[])
        p=probe('rotated',retained='tls-new');new=probe('rotated')
        record('Resource entitlement withdrawal stops established and new sessions',not p['success'] and not new['success'],{'existing':p,'new':new})
        workers['data-01'].call('mtls-grants',allowed=[m['rotated']['fingerprint']])
        p=probe('rotated')
        record('Explicit resource grant restoration recovers valid access',p['success'],p)
        # No key paths/bytes are returned. Temporary directory removes all generated material.
    record('Temporary TLS credential files removed after the exercise',not Path(tmp).exists(),{'temporary_directory_exists':Path(tmp).exists()})
