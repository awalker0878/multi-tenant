"""Bounded JSON service calls: explicit HTTPS, no redirects, proxies or retries."""
import ssl
from urllib.parse import urlsplit
from urllib.request import Request, ProxyHandler, HTTPSHandler, build_opener

from tools.neutron_observe import NoRedirect, strict_loads
from tools.run_files import encoded, require


class JsonService:
    def __init__(self, origin, authorization, ca_file=None):
        url = urlsplit(origin)
        require(url.scheme == 'https' and url.hostname and url.path in {'', '/'}
                and not url.username and not url.password and not url.query and not url.fragment,
                'Explicit HTTPS service origin required')
        require(isinstance(authorization, str) and authorization
                and not any(c in authorization for c in '\r\n'), 'Invalid service credential')
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.verify_flags |= ssl.VERIFY_X509_STRICT
        if ca_file:
            context.load_verify_locations(cafile=str(ca_file))
        else:
            context.load_default_certs(ssl.Purpose.SERVER_AUTH)
        self.origin = origin.rstrip('/')
        self.authorization = authorization
        self.opener = build_opener(ProxyHandler({}), NoRedirect(), HTTPSHandler(context=context))

    def request(self, method, path, body=None, *, etag=None, timeout=10):
        require(method in {'GET', 'POST', 'PATCH'} and path.startswith('/api/')
                and not path.startswith('//') and '#' not in path, 'Unsupported service operation')
        require(timeout > 0, 'Service contact authority expired')
        headers = {'Authorization': self.authorization, 'Accept': 'application/json',
                   'Content-Type': 'application/json'}
        if etag is not None:
            require(isinstance(etag, str) and etag not in {'', '*'}
                    and not any(c in etag for c in '\r\n'), 'Conditional object revision required')
            headers['If-Match'] = etag
        request = Request(self.origin + path, data=encoded(body) if body is not None else None,
                          headers=headers, method=method)
        with self.opener.open(request, timeout=min(timeout, 10)) as response:
            require(response.status == (201 if method == 'POST' else 200), 'Unexpected service status')
            require(response.headers.get_content_type() == 'application/json', 'Expected service JSON')
            raw = response.read(4 * 1024 * 1024 + 1)
            require(len(raw) <= 4 * 1024 * 1024, 'Service response is too large')
            return strict_loads(raw), dict(response.headers.items())
