"""Actual retained configuration drift and executing-interpreter boundaries.

The existing real sealed-runtime build campaign owns engine verification. These
negative cases cannot commission an installation or enable native effects.
"""
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from provisioner.controlplane.workflow.installed_identity import InstalledApplicationIdentity


class InstalledIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        self.output = self.root/'runtime'
        self.output.mkdir(mode=0o700)
        self.config_path = self.root/'runtime-config.json'
        self.config = {'source_commit':'a'*40,'output':str(self.output),
            'wheels':[{'name':'hosting-provisioner','sha256':'b'*64}]}
        self.save(self.config)

    def save(self, value):
        self.config_path.write_text(json.dumps(value))
        self.config_path.chmod(0o600)

    def owners(self, *, python=None, source=None, receipt=None):
        stack = ExitStack()
        stack.enter_context(patch('provisioner.controlplane.workflow.installed_identity.runtime_build.validate'))
        stack.enter_context(patch('provisioner.controlplane.workflow.installed_identity.runtime_build.artifacts'))
        stack.enter_context(patch('provisioner.controlplane.workflow.installed_identity.runtime_build.validate_receipt',
            return_value=receipt or {'source_commit':'a'*40}))
        stack.enter_context(patch('provisioner.controlplane.workflow.installed_identity.verify',
            return_value=source or {'status':'HASHES_MATCH','commit':'a'*40}))
        stack.enter_context(patch('provisioner.controlplane.workflow.installed_identity.verify_runtime',
            return_value={'status':'RUNTIME_SOURCES_MATCH'}))
        stack.enter_context(patch('provisioner.controlplane.workflow.installed_identity.sys.executable',
            python or str(self.output/'env/bin/python')))
        return stack

    def test_actual_original_configuration_drift_is_detected_at_every_use(self):
        with self.owners():
            identity = InstalledApplicationIdentity.from_configuration(self.config_path,self.root)
            self.assertEqual(identity.require_current(),('a'*40,'b'*64))
            self.save(self.config | {'newUncheckedLabel':'cannot authorize'})
            with self.assertRaises(ValueError):
                identity.require_current()

    def test_correct_version_labels_cannot_replace_actual_running_interpreter(self):
        with self.owners(python='/usr/bin/python3'):
            with self.assertRaises(ValueError):
                InstalledApplicationIdentity.from_configuration(self.config_path,self.root)

    def test_changed_source_or_original_artifact_receipt_stays_held(self):
        for options in ({'source':{'status':'HASHES_MATCH','commit':'c'*40}},
                        {'receipt':{'source_commit':'c'*40}}):
            with self.subTest(options=options),self.owners(**options),self.assertRaises(ValueError):
                InstalledApplicationIdentity.from_configuration(self.config_path,self.root)

    def test_symlinked_configuration_cannot_supply_an_installed_identity(self):
        link = self.root/'link-config.json'
        link.symlink_to(self.config_path)
        with self.owners(),self.assertRaises(ValueError):
            InstalledApplicationIdentity.from_configuration(link,self.root)
