"""Use real Cosign cryptography; every negative asserts its exact denial boundary."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tarfile
import tempfile
import unittest

from bundle import BUILDER, docker_to_oci, digest, encode, inventory, verify

ROOT = Path(__file__).resolve().parents[3]
COSIGN = os.environ.get('P01_COSIGN', 'cosign')


class BundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory();cls.work=Path(cls.temp.name);cls.root=cls.work/'bundle';cls.root.mkdir()
        cls.env=os.environ | {'COSIGN_PASSWORD':secrets.token_urlsafe(32),'HTTPS_PROXY':'http://127.0.0.1:9','HTTP_PROXY':'http://127.0.0.1:9','NO_PROXY':''}
        cls.revision='a'*40;cls.now=datetime.now(timezone.utc)
        cls.invoke(['generate-key-pair','--output-key-prefix',str(cls.work/'key')])
        layer=io.BytesIO()
        with tarfile.open(fileobj=layer,mode='w') as t:
            member=tarfile.TarInfo('synthetic-marker');raw=b'P01 synthetic image fixture';member.size=len(raw);t.addfile(member,io.BytesIO(raw))
        layer=layer.getvalue();layer_sha=hashlib.sha256(layer).hexdigest()
        config=encode({'architecture':'amd64','os':'linux','config':{'Labels':{'org.opencontainers.image.revision':cls.revision}},'rootfs':{'type':'layers','diff_ids':['sha256:'+layer_sha]}})
        cls.config='sha256:'+hashlib.sha256(config).hexdigest()
        with tarfile.open(cls.work/'image.tar','w') as t:
            for name,raw in [('manifest.json',encode([{'Config':'config.json','Layers':['layer.tar']}])),('config.json',config),('layer.tar',layer)]:
                member=tarfile.TarInfo(name);member.size=len(raw);t.addfile(member,io.BytesIO(raw))
        cls.image=docker_to_oci(cls.work/'image.tar',cls.root/'image',cls.config,cls.revision)
        for name in ['image-sbom.cdx.json','source-sbom.cdx.json']:
            (cls.root/name).write_bytes(encode({'bomFormat':'CycloneDX','components':[{'type':'file','name':'synthetic-marker'}]}))
        for scope in ['image','source']:
            (cls.root/(scope+'-scan.json')).write_bytes(encode({'scope':scope,'scanner':'trivy','version':'0.75.0','completed':True,'config_digest':cls.config,'source_revision':cls.revision,'observed_at':cls.now.isoformat(),'database':{'UpdatedAt':cls.now.isoformat()},'results':[]}))
        (cls.root/'provenance.json').write_bytes(encode({'_type':'https://in-toto.io/Statement/v1','predicateType':'https://slsa.dev/provenance/v1','subject':[{'name':'fixture','digest':{'sha256':cls.image[7:]}}],'predicate':{'buildDefinition':{'externalParameters':{'source_revision':cls.revision}},'runDetails':{'builder':{'id':BUILDER}}}}))
        cls.anchor={'scope':'p01-development','transparency':'synthetic-key-no-log','public_key_sha256':digest(cls.work/'key.pub'),'revoked':False,'source_revision':cls.revision,'component':'fixture','image_digest':cls.image,'builder_id':BUILDER}
        cls.sign(cls.root)

    @classmethod
    def invoke(cls,argv):
        p=subprocess.run([COSIGN,*argv],env=cls.env,capture_output=True,timeout=45)
        if p.returncode:raise AssertionError(p.stderr.decode())

    @classmethod
    def sign(cls,root):
        (root/'release.json').write_bytes(encode({'schema_version':1,'scope':'p01-development','component':'fixture','source_revision':cls.revision,'image':{'manifest_digest':cls.image,'config_digest':cls.config,'platform':'linux/amd64'},'files':inventory(root,('release.json','signature.sigstore.json'))}))
        cls.invoke(['sign-blob','--yes','--signing-config',str(ROOT/'release/development-signing.json'),'--key',str(cls.work/'key.key'),'--bundle',str(root/'signature.sigstore.json'),str(root/'release.json')])
        bundle=json.loads((root/'signature.sigstore.json').read_text())
        if bundle['verificationMaterial'].get('tlogEntries'):raise AssertionError('Development fixture must not publish to a transparency log')

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        self.copy=self.work/'case'
        if self.copy.exists():shutil.rmtree(self.copy)
        shutil.copytree(self.root,self.copy)

    def verify(self,anchor=None,key=None):
        return verify(self.copy,anchor or self.anchor,key or self.work/'key.pub',COSIGN,self.now)

    def test_accepts_signed_bound_fixture(self):self.assertEqual(self.verify()['result'],'ADMITTED_DEVELOPMENT')

    def test_unsigned_rejected(self):
        (self.copy/'signature.sigstore.json').unlink()
        with self.assertRaisesRegex(ValueError,'^missing_signature$'):self.verify()

    def test_altered_manifest_rejected(self):
        with (self.copy/'release.json').open('ab') as out:out.write(b' ')
        with self.assertRaisesRegex(ValueError,'^signature_invalid$'):self.verify()

    def test_altered_layer_sbom_and_missing_scan_rejected(self):
        for name in ['image-sbom.cdx.json','image-scan.json','image/blobs/sha256/'+self.config[7:]]:
            with self.subTest(name=name):
                p=self.copy/name;raw=p.read_bytes();p.write_bytes(raw+b'changed')
                with self.assertRaisesRegex(ValueError,'^bundle_content_mismatch$'):self.verify()
                p.write_bytes(raw)

    def test_wrong_source_and_digest_rejected(self):
        for key,value,code in [('source_revision','b'*40,'manifest_identity_mismatch'),('image_digest','sha256:'+'b'*64,'image_manifest_mismatch')]:
            with self.assertRaisesRegex(ValueError,'^'+code+'$'):self.verify(dict(self.anchor,**{key:value}))

    def test_wrong_or_revoked_key_rejected(self):
        with self.assertRaisesRegex(ValueError,'^untrusted_signer$'):self.verify(dict(self.anchor,public_key_sha256='b'*64))
        with self.assertRaisesRegex(ValueError,'^revoked_signer$'):self.verify(dict(self.anchor,revoked=True))

    def test_bundle_cannot_supply_own_anchor(self):
        shutil.copyfile(self.work/'key.pub',self.copy/'key.pub')
        with self.assertRaisesRegex(ValueError,'^self_supplied_trust_root$'):self.verify(key=self.copy/'key.pub')

    def test_no_operated_scope_upgrade(self):
        with self.assertRaisesRegex(ValueError,'^operated_trust_not_configured$'):self.verify(dict(self.anchor,scope='production'))

    def test_even_signed_missing_and_stale_scans_rejected(self):
        p=self.copy/'source-scan.json';original=p.read_bytes();d=json.loads(original);d['completed']=False;p.write_bytes(encode(d));self.sign(self.copy)
        with self.assertRaisesRegex(ValueError,'^invalid_scan$'):self.verify()
        d=json.loads(original);d['observed_at']=(self.now-timedelta(days=2)).isoformat();p.write_bytes(encode(d));self.sign(self.copy)
        with self.assertRaisesRegex(ValueError,'^stale_scan$'):self.verify()

    def test_even_signed_security_findings_block(self):
        p=self.copy/'image-scan.json';d=json.loads(p.read_text());d['results']=[{'Vulnerabilities':[{'VulnerabilityID':'CVE-SYNTHETIC','Severity':'HIGH'}]}];p.write_bytes(encode(d));self.sign(self.copy)
        with self.assertRaisesRegex(ValueError,'^security_findings:CVE-SYNTHETIC$'):self.verify()

    def test_unexpected_file_and_symlink_rejected(self):
        (self.copy/'injected').write_text('unexpected')
        with self.assertRaisesRegex(ValueError,'^bundle_content_mismatch$'):self.verify()
        (self.copy/'injected').unlink();(self.copy/'link').symlink_to(self.work/'key.pub')
        with self.assertRaisesRegex(ValueError,'^symlinked_bundle_path$'):self.verify()

    def test_build_once_transfer_keeps_every_byte(self):
        before=inventory(self.copy);target=self.work/'receiving-store';shutil.copytree(self.copy,target)
        self.assertEqual(inventory(target),before)
        self.assertEqual(verify(target,self.anchor,self.work/'key.pub',COSIGN,self.now)['image_digest'],self.image)


if __name__=='__main__':unittest.main()
