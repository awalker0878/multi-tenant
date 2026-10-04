#!/usr/bin/env python3
"""Prepare a disposable P01 TLS installation; never start or pull containers."""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
from typing import Mapping


SERVICES = ("console", "governance", "catalogue", "assurance", "planning", "inventory", "lifecycle")
PHP_SERVICES = frozenset(SERVICES[:4])
IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}\Z")
REVISION = re.compile(r"[0-9a-f]{40}\Z")


def _write(path: Path, value: str, mode: int = 0o444) -> None:
    path.write_text(value, encoding="utf-8")
    path.chmod(mode)


def _openssl(*arguments: str) -> None:
    # Do not emit key material or command output into evidence or logs.
    result = subprocess.run(["openssl", *arguments], capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError("OpenSSL could not generate the private local TLS fixture")


def _certificates(directory: Path) -> None:
    ca_key, ca_cert = directory / "ca.key", directory / "ca.crt"
    _openssl("req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256",
             "-nodes", "-keyout", str(ca_key), "-out", str(ca_cert), "-days", "7", "-sha256",
             "-subj", "/CN=P01 disposable local CA", "-addext", "basicConstraints=critical,CA:TRUE",
             "-addext", "keyUsage=critical,keyCertSign,cRLSign")
    ca_key.chmod(0o400)
    ca_cert.chmod(0o444)
    for service in (*SERVICES, "postgres"):
        key, cert = directory / f"{service}.key", directory / f"{service}.crt"
        csr, extensions = directory / f"{service}.csr", directory / f"{service}.ext"
        san = f"DNS:{service}" if service == "postgres" else f"DNS:{service},DNS:localhost,IP:127.0.0.1"
        _write(extensions, "basicConstraints=critical,CA:FALSE\n"
               "keyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth\n"
               f"subjectAltName={san}\n", 0o600)
        _openssl("req", "-new", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256",
                 "-nodes", "-keyout", str(key), "-out", str(csr), "-subj", f"/CN={service}")
        _openssl("x509", "-req", "-in", str(csr), "-CA", str(ca_cert), "-CAkey", str(ca_key),
                 "-set_serial", str(secrets.randbits(128) + 1), "-days", "7", "-sha256",
                 "-extfile", str(extensions), "-out", str(cert))
        key.chmod(0o444)
        cert.chmod(0o444)
        csr.unlink()
        extensions.unlink()


def _nginx(service: str) -> str:
    common = """pid /tmp/nginx.pid;
error_log /dev/stderr warn;
events { worker_connections 128; }
http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    access_log off;
    server_tokens off;
    client_body_temp_path /tmp/client_body;
    proxy_temp_path /tmp/proxy;
    fastcgi_temp_path /tmp/fastcgi;
    uwsgi_temp_path /tmp/uwsgi;
    scgi_temp_path /tmp/scgi;
    server {
        listen 8443 ssl;
        server_name SERVICE localhost;
        if ($host !~ ^(SERVICE|localhost|127\\.0\\.0\\.1)$) { return 421; }
        ssl_certificate /run/secrets/tls.crt;
        ssl_certificate_key /run/secrets/tls.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        add_header X-Content-Type-Options nosniff always;
        location ~ (^|/)\\. { return 404; }
        location ~* ^/(app|bootstrap|config|database|resources|routes|storage|vendor)(/|$) { return 404; }
        location ~* ^/(composer\\.(json|lock)|package(-lock)?\\.json|artisan|Dockerfile|pyproject\\.toml|uv\\.lock)(/|$) { return 404; }
""".replace("SERVICE", service)
    if service in PHP_SERVICES:
        body = """        root /srv/public;
        index index.php;
        location / { try_files $uri $uri/ /index.php?$query_string; }
        location = /index.php {
            include /etc/nginx/fastcgi_params;
            fastcgi_param SCRIPT_FILENAME /app/public/index.php;
            fastcgi_param DOCUMENT_ROOT /app/public;
            fastcgi_param HTTPS on;
            fastcgi_pass SERVICE:9000;
        }
        location ~* \\.php(?:/|$) { return 404; }
""".replace("SERVICE", service)
    else:
        body = """        location / {
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-Proto https;
            proxy_set_header X-Forwarded-For $remote_addr;
            proxy_pass http://SERVICE:8080;
        }
""".replace("SERVICE", service)
    return common + body + "    }\n}\n"


def _bind(source: Path, target: str) -> dict[str, object]:
    return {"type": "bind", "source": str(source), "target": target, "read_only": True,
            "bind": {"create_host_path": False}}


def _secret(source: str, target: str | None = None) -> dict[str, str]:
    return {"source": source, "target": target or source}


def _base(image: str) -> dict[str, object]:
    return {"image": image, "platform": "linux/amd64", "pull_policy": "never",
            "read_only": True, "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges:true"], "init": True}


def _inputs(root: Path, images: Mapping[str, str], revision: str) -> dict[str, str]:
    if not isinstance(revision, str) or REVISION.fullmatch(revision) is None:
        raise ValueError("Source revision must be a full lowercase 40-character Git commit")
    if not isinstance(images, Mapping) or set(images) != set(SERVICES):
        raise ValueError("Images must contain exactly the seven P01 application service IDs")
    if any(not isinstance(value, str) or IMAGE_ID.fullmatch(value) is None for value in images.values()):
        raise ValueError("Application images must be immutable local sha256 image configuration IDs")
    lock = json.loads((root / "deploy/dependencies/inputs.lock.json").read_text(encoding="utf-8"))
    if lock.get("platform") != "linux/amd64":
        raise ValueError("Dependency image lock must describe linux/amd64")
    dependencies = {}
    for service in ("nginx", "postgres"):
        entry = lock["images"][service]
        digest = entry.get("digest", "")
        reference = entry.get("reference", "")
        if not isinstance(digest, str) or IMAGE_ID.fullmatch(digest) is None:
            raise ValueError(f"The {service} dependency digest is not immutable")
        if reference != f"docker.io/library/{service}@{digest}":
            raise ValueError(f"The {service} dependency reference must match its official-image digest")
        dependencies[service] = reference
    for script in ("entrypoint.sh", "initialize.sh", "migrate.sql"):
        if not (root / "deploy/dependencies/postgres" / script).is_file():
            raise ValueError(f"Missing PostgreSQL fixture script: {script}")
    return dependencies


def prepare(root: Path, runtime: Path, images: Mapping[str, str], revision: str) -> Path:
    """Create compose.json in an absent directory under an owned private host parent.

    The caller extracts each PHP image's public directory into public/<service> before
    starting Compose. No supplied application image is pulled, retagged or rebuilt.
    """
    root, runtime = Path(root).resolve(strict=True), Path(runtime)
    dependencies = _inputs(root, images, revision)
    if not runtime.is_absolute():
        raise ValueError("Runtime directory must be absolute")
    if runtime.exists() or runtime.is_symlink():
        raise ValueError("Runtime directory must not already exist")
    runtime = runtime.resolve()
    if runtime == root or runtime.is_relative_to(root):
        raise ValueError("Runtime directory must be outside the source workspace")
    parent = runtime.parent.stat()
    if stat.S_IMODE(parent.st_mode) != 0o700 or parent.st_uid != os.geteuid():
        raise ValueError("Runtime parent must be owned by this user with mode 0700")
    runtime.mkdir(mode=0o700)
    try:
        secret_dir = runtime / "secrets"
        secret_dir.mkdir(mode=0o700)
        (runtime / "nginx").mkdir()
        (runtime / "public").mkdir()
        for service in SERVICES:
            for identity in ("runtime", "migrator"):
                _write(secret_dir / f"{service}-{identity}-password", secrets.token_urlsafe(32) + "\n")
            _write(secret_dir / f"{service}-health-token", secrets.token_urlsafe(32) + "\n")
            if service in PHP_SERVICES:
                _write(secret_dir / f"{service}-app-key", "base64:" + base64.b64encode(secrets.token_bytes(32)).decode() + "\n")
                (runtime / "public" / service).mkdir()
            _write(runtime / "nginx" / f"{service}.conf", _nginx(service))
        _write(secret_dir / "postgres-password", secrets.token_urlsafe(32) + "\n")
        _certificates(secret_dir)

        services: dict[str, object] = {}
        networks: dict[str, object] = {}
        secret_sources = {path.name: {"file": str(path)} for path in secret_dir.iterdir() if path.name != "ca.key"}
        for service in SERVICES:
            networks[f"db_{service}"] = {"internal": True}
            networks[f"web_{service}"] = {"internal": True}
            environment = {"APP_ENV": "production", "APP_DEBUG": "false", "DB_HOST": "postgres",
                           "DB_PORT": "5432", "DB_DATABASE": service, "DB_USERNAME": f"{service}_runtime",
                           "DB_PASSWORD_FILE": "/run/secrets/db-password", "DB_SSLMODE": "verify-full",
                           "DB_SSLROOTCERT": "/run/secrets/ca.crt", "HEALTH_TOKEN_FILE": "/run/secrets/health-token"}
            app = _base(images[service])
            app.update(user="10001:10001", networks=[f"db_{service}", f"web_{service}"],
                       environment=environment, depends_on={"postgres": {"condition": "service_started"}},
                       secrets=[_secret(f"{service}-runtime-password", "db-password"), _secret("ca.crt"),
                                _secret(f"{service}-health-token", "health-token")],
                       tmpfs=["/tmp:rw,noexec,nosuid,size=32m,uid=10001,gid=10001,mode=1777"])
            if service in PHP_SERVICES:
                environment["APP_KEY_FILE"] = "/run/secrets/app-key"
                app["secrets"].append(_secret(f"{service}-app-key", "app-key"))
                app["tmpfs"].extend(["/app/storage:rw,noexec,nosuid,size=32m,uid=10001,gid=10001,mode=0770",
                                     "/app/bootstrap/cache:rw,noexec,nosuid,size=16m,uid=10001,gid=10001,mode=0770"])
                app["command"] = ["sh", "-ec", "php artisan config:cache && exec php-fpm -F"]
            else:
                app["entrypoint"] = [f"/opt/venv/bin/{service}-serve"]
                app["command"] = []
            services[service] = app
            proxy = _base(dependencies["nginx"])
            proxy.update(user="10001:10001", entrypoint=["/usr/sbin/nginx"], command=["-g", "daemon off;"],
                         networks=[f"web_{service}"], depends_on={service: {"condition": "service_started"}},
                         ports=[{"target": 8443, "host_ip": "127.0.0.1", "protocol": "tcp"}],
                         tmpfs=["/tmp:rw,noexec,nosuid,size=32m,uid=10001,gid=10001,mode=1777"],
                         secrets=[_secret(f"{service}.crt", "tls.crt"), _secret(f"{service}.key", "tls.key")],
                         volumes=[_bind(runtime / "nginx" / f"{service}.conf", "/etc/nginx/nginx.conf")])
            if service in PHP_SERVICES:
                proxy["volumes"].append(_bind(runtime / "public" / service, "/srv/public"))
            services[f"{service}-proxy"] = proxy

        postgres = _base(dependencies["postgres"])
        pg_scripts = root / "deploy/dependencies/postgres"
        postgres.update(user="0:0", entrypoint=["/bin/bash", "/opt/foundation/entrypoint.sh"],
                        command=["postgres"], cap_add=["CHOWN", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID"],
                        healthcheck={"test": ["CMD", "pg_isready", "-h", "127.0.0.1", "-U", "postgres"],
                                     "interval": "2s", "timeout": "2s", "retries": 30},
                        networks=[f"db_{service}" for service in SERVICES],
                        volumes=[{"type": "volume", "source": "postgres_data", "target": "/var/lib/postgresql"},
                                 _bind(pg_scripts / "entrypoint.sh", "/opt/foundation/entrypoint.sh"),
                                 _bind(pg_scripts / "initialize.sh", "/docker-entrypoint-initdb.d/10-private-identities.sh"),
                                 _bind(pg_scripts / "migrate.sql", "/opt/foundation/migrate.sql")],
                        tmpfs=["/tmp:rw,noexec,nosuid,size=64m,mode=1777", "/var/run/postgresql:rw,noexec,nosuid,size=16m,mode=1777"],
                        secrets=[_secret(name) for name in ("postgres-password", "postgres.key", "postgres.crt", "ca.crt")]
                        + [_secret(f"{service}-{identity}-password") for service in SERVICES for identity in ("runtime", "migrator")])
        services["postgres"] = postgres
        document = {"name": f"p01-{revision[:12]}-{secrets.token_hex(4)}", "services": services,
                    "networks": networks, "volumes": {"postgres_data": {}}, "secrets": secret_sources}
        destination = runtime / "compose.json"
        _write(destination, json.dumps(document, indent=2, sort_keys=True) + "\n", 0o600)
        return destination
    except BaseException:
        shutil.rmtree(runtime)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    generate = subcommands.add_parser("generate", help="Prepare a private Compose installation without starting it")
    generate.add_argument("--workspace", type=Path, required=True)
    generate.add_argument("--runtime", type=Path, required=True)
    generate.add_argument("--images", required=True, help="JSON object or path to JSON mapping seven service IDs to local image IDs")
    generate.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    try:
        images = json.loads(args.images if args.images.lstrip().startswith("{") else Path(args.images).read_text(encoding="utf-8"))
        print(prepare(args.workspace, args.runtime, images, args.source_revision))
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        parser.exit(1, f"Cannot prepare P01 runtime: {error}\n")


if __name__ == "__main__":
    main()
