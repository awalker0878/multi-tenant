"""Installed composition of current qualification and minimum operating gates."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import ssl

from provisioner.controlplane.evidence.runtime import EvidenceRuntimeConfig, _private_file
from provisioner.controlplane.evidence.vault import VaultTransitClient, VaultTransitVerifier
from provisioner.qualification.action_gate import SelectedQualificationGate
from .action_gate import OperationsActionGate, QualifiedOperatingActionGate

_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')


def build_action_gate(evidence_gate, *, environment=None, verifier_client=None, worker_grants=None):
    """No permissive default: absent site operating-signature custody stops startup."""
    env = os.environ if environment is None else environment
    config = EvidenceRuntimeConfig.from_environment(env)
    trust_raw = env.get('HOSTING_OPS_ACCEPTANCE_VAULT_TRUST_JSON')
    if not isinstance(trust_raw, str) or len(trust_raw) > 16384:
        raise ValueError('Distinct current operating-acceptance key custody must be configured')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate operating-signature custody key')
            result[key] = value
        return result
    trust = json.loads(trust_raw, object_pairs_hook=pairs)
    if (not isinstance(trust, dict) or not trust or len(trust) > 32
            or any(not isinstance(label, str) or not _NAME.fullmatch(label)
                   or not isinstance(pair, list) or len(pair) != 2
                   or not all(isinstance(item, str) and _NAME.fullmatch(item) for item in pair)
                   for label, pair in trust.items())
            or set(trust) & set(config.trusted_keys)
            or {tuple(pair) for pair in trust.values()} & set(config.trusted_keys.values())):
        raise ValueError('Operating acceptance must use independent reviewed keys, not checkpoint keys')
    if verifier_client is None:
        tls = ssl.create_default_context(cafile=str(config.vault_ca))
        tls.minimum_version = ssl.TLSVersion.TLSv1_2
        verifier_client = VaultTransitClient(config.vault_url,
            lambda: _private_file(config.vault_verify_token_file), tls_context=tls)
    verifier = VaultTransitVerifier(verifier_client, {key: tuple(pair) for key, pair in trust.items()})
    path_names = {
        'qualification_path': 'HOSTING_QUALIFICATION_INDEX',
        'provenance_path': 'HOSTING_VERSION_PROVENANCE_INDEX',
        'campaign_path': 'HOSTING_QUALIFICATION_CAMPAIGN_INDEX',
        'target_selection_path': 'HOSTING_TARGET_SELECTION_INDEX',
        'capacity_path': 'HOSTING_CAPACITY_INDEX',
    }
    qualification = SelectedQualificationGate(**{
        key: Path(env[name]) for key, name in path_names.items() if env.get(name)})
    operations = OperationsActionGate(evidence_gate=evidence_gate, operating_verifier=verifier,
                                      operating_key_ids=frozenset(trust), worker_grants=worker_grants)
    return QualifiedOperatingActionGate(qualification, operations)
