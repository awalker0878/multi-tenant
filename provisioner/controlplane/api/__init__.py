"""HTTP transport for the enterprise control plane.

An application must be constructed with its real authority, record store and
job repository. This package deliberately has no module-level application or
credential fallback.
"""

from .http import create_app

__all__ = ['create_app']
