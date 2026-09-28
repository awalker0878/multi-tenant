"""Self-hosted, opt-in sysadmin portal for the scoped control API.

The portal only displays persisted API data. It never manufactures discovery,
provisioning or migration progress. A configured HTTPS OIDC public client with
Authorization Code, PKCE S256 and form_post support is required to mount it.
"""

from .routes import PortalConfig, mount_portal

__all__ = ['PortalConfig', 'mount_portal']
