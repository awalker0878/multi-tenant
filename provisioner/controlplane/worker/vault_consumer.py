"""Consume one enrolled dynamic Vault credential without exposing agent tokens.

The response's shape belongs to a concrete native/service consumer. This owner
only performs the real one-use HTTPS unwrap and verifies the exact live grant,
enrolled role, response bounds and revocable backend lease.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import http.client
import ssl

from provisioner.controlplane.authority.model import WorkerGrant
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import digest
from .grants import GrantDenied
from .vault import VaultDynamicCredentialIssuer, VaultWrappedCredential


@dataclass(frozen=True)
class ConsumedVaultCredential:
    data: dict = field(repr=False)
    expires_at: datetime
    lease_digest: str
    role_reference: str


class VaultCredentialConsumer:
    def __init__(self, issuer: VaultDynamicCredentialIssuer):
        if not isinstance(issuer, VaultDynamicCredentialIssuer):
            raise TypeError('A concrete independently enrolled dynamic Vault issuer is required')
        self.issuer = issuer

    def unwrap(self, handle: VaultWrappedCredential, grant: WorkerGrant) -> ConsumedVaultCredential:
        now = datetime.now(timezone.utc)
        if (not isinstance(handle, VaultWrappedCredential) or not isinstance(grant, WorkerGrant)
                or handle.grant_id != grant.grant_id or not now < handle.expires_at <= grant.expires_at):
            raise GrantDenied('The single-use credential must belong to the current grant')
        roles = [role for role in self.issuer._roles.values()
                 if handle.creation_path in (role.api_path, '/v1/' + role.api_path)]
        if (len(roles) != 1 or roles[0].scope != grant.operation_scope
                or roles[0].operation_kind != grant.operation_kind):
            raise GrantDenied('Credential creation path differs from the enrolled role and scope')
        headers = {'X-Vault-Token': handle.wrapping_token, 'X-Vault-Request': 'true',
                   'Accept': 'application/json', 'Content-Type': 'application/json'}
        if self.issuer._namespace is not None:
            headers['X-Vault-Namespace'] = self.issuer._namespace
        connection = http.client.HTTPSConnection(self.issuer._host, self.issuer._port,
            timeout=min(self.issuer._timeout, (handle.expires_at-now).total_seconds()),
            context=self.issuer._tls)
        try:
            connection.request('POST', '/v1/sys/wrapping/unwrap', body=b'{}', headers=headers)
            response = connection.getresponse()
            raw = response.read(65537)
            if (response.status != 200 or len(raw) > 65536
                    or response.headers.get_content_type() != 'application/json'):
                raise GrantDenied('Vault did not return a bounded single-use credential')
            payload = strict_loads(raw)
            seconds, lease = payload.get('lease_duration'), payload.get('lease_id')
            data = payload.get('data')
            if (not isinstance(lease, str) or not 1 <= len(lease) <= 4096
                    or type(seconds) is not int
                    or not 0 < seconds <= int(roles[0].max_credential_ttl.total_seconds())
                    or type(data) is not dict or payload.get('auth') is not None
                    or payload.get('wrap_info') is not None):
                raise GrantDenied('A revocable bounded native credential lease is required')
            expiry = min(handle.expires_at, grant.expires_at,
                         datetime.now(timezone.utc) + timedelta(seconds=seconds))
            if expiry <= datetime.now(timezone.utc):
                raise GrantDenied('Native credential expired during consumption')
            if self.issuer._lease_store is not None:
                self.issuer._lease_store.consumed(handle,grant,lease,expiry)
            return ConsumedVaultCredential(data, expiry, digest(lease.encode()), roles[0].reference)
        except (OSError, TimeoutError, ssl.SSLError, http.client.HTTPException,
                ValueError, KeyError, UnicodeError) as exc:
            raise GrantDenied('Enrolled native credential consumption failed') from exc
        finally:
            connection.close()
