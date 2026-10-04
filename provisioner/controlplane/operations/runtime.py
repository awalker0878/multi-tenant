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
    (observer, observer_keys), _ = build_operating_verifiers(environment=env, verifier_client=verifier_client)
    operations = OperationsActionGate(evidence_gate=evidence_gate, operating_verifier=verifier,
        operating_key_ids=frozenset(trust), worker_grants=worker_grants,
        observer_verifier=observer, observer_key_ids=observer_keys)
    return QualifiedOperatingActionGate(qualification, operations)


def build_operating_verifiers(*, environment=None, verifier_client=None):
    """Separate observer and operating owner keys, including actual Vault paths."""
    env = os.environ if environment is None else environment
    config = EvidenceRuntimeConfig.from_environment(env)
    trusts = []
    used_ids, used_paths = set(config.trusted_keys), set(config.trusted_keys.values())
    # Also exclude the existing B44-B46 acceptance key: observing a drill and
    # accepting its handover are distinct responsibilities from its prerequisite.
    acceptance = json.loads(env['HOSTING_OPS_ACCEPTANCE_VAULT_TRUST_JSON'])
    if not isinstance(acceptance, dict):
        raise ValueError('Current minimum operating acceptance trust required')
    used_ids.update(acceptance)
    used_paths.update(tuple(pair) for pair in acceptance.values())
    for variable in ('HOSTING_RELEASE_VAULT_TRUST_JSON', 'HOSTING_PILOT_ACCEPTANCE_VAULT_TRUST_JSON'):
        if env.get(variable):
            peer = json.loads(env[variable])
            if not isinstance(peer, dict):
                raise ValueError('Current release/receiving peer custody must be strict')
            used_ids.update(peer)
            used_paths.update(tuple(pair) for pair in peer.values())
    for variable in ('HOSTING_NATIVE_OBSERVER_VAULT_TRUST_JSON', 'HOSTING_OPERATING_HANDOVER_VAULT_TRUST_JSON'):
        def pairs(items):
            value = {}
            for key, item in items:
                if key in value:
                    raise ValueError('Duplicate dedicated operating custody alias')
                value[key] = item
            return value
        raw = env[variable]
        if len(raw) > 16384:
            raise ValueError('Bounded separately reviewed operating trust required')
        trust = json.loads(raw, object_pairs_hook=pairs)
        if (not isinstance(trust, dict) or not 1 <= len(trust) <= 32
                or any(not isinstance(key, str) or not _NAME.fullmatch(key)
                       or not isinstance(pair, list) or len(pair) != 2
                       or any(not isinstance(item, str) or not _NAME.fullmatch(item) for item in pair)
                       for key, pair in trust.items())
                or used_ids & set(trust) or used_paths & {tuple(pair) for pair in trust.values()}):
            raise ValueError('Observer/operating/checkpoint/acceptance custodians must be distinct')
        used_ids.update(trust)
        used_paths.update(tuple(pair) for pair in trust.values())
        trusts.append(trust)
    if verifier_client is None:
        tls = ssl.create_default_context(cafile=str(config.vault_ca))
        tls.minimum_version = ssl.TLSVersion.TLSv1_2
        verifier_client = VaultTransitClient(config.vault_url,
            lambda: _private_file(config.vault_verify_token_file), tls_context=tls)
    return tuple((VaultTransitVerifier(verifier_client, {key: tuple(pair) for key, pair in trust.items()}),
                  frozenset(trust)) for trust in trusts)


def build_instance_gate(evidence_gate, *, source_commit: str, artifact_sha256: str,
                        environment=None, verifier_client=None, installed_identity=None):
    from .instance import OperatingInstanceGate
    (observer, observer_keys), (operating, operating_keys) = build_operating_verifiers(
        environment=environment, verifier_client=verifier_client)
    return OperatingInstanceGate(evidence_gate=evidence_gate, observer_verifier=observer,
        observer_key_ids=observer_keys, operating_verifier=operating,
        operating_key_ids=operating_keys, source_commit=source_commit, artifact_sha256=artifact_sha256,
        installed_identity=installed_identity)
