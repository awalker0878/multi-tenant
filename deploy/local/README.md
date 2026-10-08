# P01 disposable local installation

`scripts/p01/local_runtime.py` generates an isolated Docker Compose installation for
the seven foundation applications and TLS PostgreSQL 18. It consumes each application's
immutable local image configuration ID and the observed official Nginx/PostgreSQL
manifest references in `deploy/dependencies/inputs.lock.json`. Every Compose service
uses `pull_policy: never`; generation performs no Docker operations or downloads.

Run the measured installation campaign from a clean checkout:

```sh
python scripts/p01/run_local.py \
  --workspace /absolute/path/to/checkout \
  --source-revision FULL_40_CHARACTER_COMMIT \
  --output /absolute/path/to/absent-evidence-directory
```

The campaign builds the seven owned images, pulls the locked dependency manifests,
generates private credentials and a disposable CA, extracts the PHP images' public
files, starts PostgreSQL, applies each database migration using its own authenticated
migrator, and starts the applications. Optional `--images /absolute/path/to/images.json`
reuses a JSON object mapping `console`, `governance`, `catalogue`, `assurance`, `planning`,
`inventory`, and `lifecycle` to local `sha256:` image configuration IDs.

The campaign checks verified TLS, authenticated dependency diagnostics, rejected
credentials, database and DDL isolation, credential revocation, schema drift, dependency
loss, and database restart persistence. These checks measure foundation behavior with
synthetic data. `/health/live` describes the process, `/health/dependencies` requires the
service's private health token, and product `/health/ready` remains HTTP 503. Broker,
Temporal, evidence storage, workers, native operations, full restore, Kubernetes, and
operating acceptance are outside this installation.

## Generate without starting containers

Create a private parent directory owned by the current user with mode `0700`. The
runtime child must be absolute, absent, and outside the source checkout:

```sh
python scripts/p01/local_runtime.py generate \
  --workspace /absolute/path/to/checkout \
  --runtime /absolute/path/to/private-parent/new-runtime \
  --images /absolute/path/to/images.json \
  --source-revision FULL_40_CHARACTER_COMMIT
```

The library API is `prepare(root, runtime, images, revision) -> Path`; its return value
is the generated `compose.json` path. `--images` also accepts the JSON object directly.
Generation refuses mutable application tags, foreign or mutable dependency references,
missing service image IDs, existing runtime paths, and nonprivate parent directories.
It requires Python 3.12 and OpenSSL; the execution campaign additionally requires Git,
Docker Engine, and Docker Compose.

The runtime directory contains:

| Path | Contents |
| --- | --- |
| `compose.json` | Nonsecret configuration, immutable image identities, private file paths, and a unique Compose project name |
| `secrets/` | Separate runtime/migrator passwords, health tokens, PHP application keys, disposable TLS certificates and private keys |
| `nginx/<service>.conf` | TLS proxy configuration for exactly one application |
| `public/<php-service>/` | Initially empty; the campaign copies only that immutable image's `/app/public` contents before starting proxies |

The generated CA key is never mounted into any container. Mounted secret files are
`0444` to support their different unprivileged container readers; their host runtime
and parent directories are `0700`. Secret values never appear in Compose environment
variables or generated configuration. Do not copy runtime secrets into evidence,
source control, or build contexts. Certificates last seven days; regenerate the
disposable installation when they expire.

## Isolation and lifecycle

Each application joins its own internal database network and its own internal proxy
network. PostgreSQL joins the seven database networks. Each Nginx proxy joins its
application's proxy network and a separate bridge used only by that proxy to publish
the loopback TLS port. Docker requires a noninternal bridge for host port publication;
this bridge disables IP masquerading and no application joins it. Applications,
database ports, and PHP FPM ports have no
host mappings. Only TLS port 8443 on each proxy publishes to an automatically assigned
port on `127.0.0.1`. The campaign records those assigned ports.

Nginx and application processes run as UID/GID `10001`, with read-only root filesystems,
all capabilities dropped, and `no-new-privileges`. Nginx accepts only the owning service,
`localhost`, or `127.0.0.1` as Host; other hosts receive HTTP 421. PHP proxies mount only
the extracted public root, execute only `/app/public/index.php`, and reject dotfiles,
other PHP paths, and source/configuration paths. Python proxies forward to their owning
HTTP process on port 8080. Access logs are disabled. PHP generates its production
configuration cache at startup in an owned temporary directory.

PostgreSQL starts through the repository's TLS wrapper with only the capabilities
needed to initialize its owned volume and drop privileges. Its durable volume mounts
at `/var/lib/postgresql` for the PostgreSQL 18 layout; TLS key copies and sockets use
temporary filesystems. Runtime clients verify the server certificate against the
generated CA and connect using distinct credentials to their own database. PostgreSQL
receives database credentials and its own TLS material, but no application health
credentials, application keys, proxy keys, or CA private key.

The campaign normally removes its unique Compose project, database volume, and private
runtime files after collecting nonsecret evidence. `--keep` retains the installation
for inspection; remove that exact project with `docker compose -f /path/to/runtime/compose.json
down --volumes --remove-orphans`, then remove its private runtime directory. An existing
installation is never adopted or overwritten by generation.

Run installer validation without Docker or network access:

```sh
python -m unittest discover -s scripts/p01 -p test_local_runtime.py -v
```

These structural and certificate tests cover image pinning, loopback publication,
network/secret ownership, unprivileged execution, certificate trust and names, private
runtime placement, and refusal to overwrite an existing installation. Successful
generation alone does not establish that the actual installation campaign passed.
