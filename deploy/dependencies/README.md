# P01 synthetic dependency installation

P01.02/P01.05 first implement real TLS PostgreSQL connections, service-private databases,
runtime/migrator identities and private health credentials. Dependency health is separate
from product readiness and native authority. The selected Nginx candidate supplies actual
TLS/FastCGI ingress for PHP foundations. `candidates.json` contains exact version candidates;
the observation workflow records immutable platform manifests before installation.

The development PostgreSQL selection is the previously measured 18.6 Bookworm amd64
image from P00, copied with its source provenance into the product dependency input lock.
No product runtime imports spike code. Connected candidate downloads do not qualify an
operating mirror, production support or signed promotion. Broker, Temporal and evidence
storage join readiness only when their actual clients and required behaviors are implemented.
