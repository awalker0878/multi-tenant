"""Repository-side portable provisioning core.

This package turns a portable workload-security-domain request into reviewed,
disabled infrastructure inputs. It never contacts a native platform, holds no
credentials and grants no authorization: every artifact it produces is a draft
that still requires independent native qualification and separate production
approval.
"""
from __future__ import annotations

from provisioner.domain.errors import Diagnostics, ProvisioningError

__all__ = ['Diagnostics', 'ProvisioningError', 'FORMAT_VERSION']
FORMAT_VERSION = '1.0'