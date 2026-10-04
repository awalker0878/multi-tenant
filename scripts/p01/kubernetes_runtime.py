#!/usr/bin/env python3
"""Render a private synthetic kind foundation; rendering never establishes a pass."""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import re
import secrets
import shutil
from typing import Mapping

import local_runtime

SERVICES = local_runtime.SERVICES
PHP_SERVICES = local_runtime.PHP_SERVICES
NAMESPACE = re.compile(r"p01-[a-z0-9](?:[a-z0-9-]{0,55}[a-z0-9])?\Z")
NODE_IMAGE = re.compile(r"kindest/node:v1\.36\.\d+@sha256:[a-f0-9]{64}\Z")


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _list(items: list[dict]) -> dict:
    return {"apiVersion": "v1", "kind": "List", "items": items}


def _object(kind: str, name: str, namespace: str, **fields: object) -> dict:
    api = {"Deployment": "apps/v1", "Job": "batch/v1", "NetworkPolicy": "networking.k8s.io/v1"}.get(kind, "v1")
    return {"apiVersion": api, "kind": kind, "metadata": {"name": name, "namespace": namespace}, **fields}


def _labels(role: str, service: str) -> dict[str, str]:
    return {"app.kubernetes.io/part-of": "p01-foundation", "p01.role": role, "p01.service": service}


def _peer(role: str, service: str) -> dict:
    return {"podSelector": {"matchLabels": _labels(role, service)}}


def _port(port: int) -> dict:
    return {"port": port, "protocol": "TCP"}


def _container(name: str, image: str, memory: str = "256Mi") -> dict:
    return {"name": name, "image": image, "imagePullPolicy": "Never",
            "securityContext": {"runAsUser": 10001, "runAsGroup": 10001, "runAsNonRoot": True,
                                "readOnlyRootFilesystem": True, "allowPrivilegeEscalation": False,
                                "capabilities": {"drop": ["ALL"]}},
            "resources": {"requests": {"cpu": "25m", "memory": "64Mi"},
                          "limits": {"cpu": "1", "memory": memory}}}


def _pod(name: str, containers: list[dict], volumes: list[dict]) -> dict:
    return {"serviceAccountName": name, "automountServiceAccountToken": False,
            "enableServiceLinks": False, "terminationGracePeriodSeconds": 30,
            "securityContext": {"runAsNonRoot": True, "runAsUser": 10001,
                                "runAsGroup": 10001, "fsGroup": 10001,
                                "seccompProfile": {"type": "RuntimeDefault"}},
            "containers": containers, "volumes": volumes}


def _deployment(name: str, namespace: str, labels: dict, pod: dict) -> dict:
    return _object("Deployment", name, namespace, spec={"replicas": 1,
                   "strategy": {"type": "Recreate"}, "selector": {"matchLabels": labels},
                   "template": {"metadata": {"labels": labels}, "spec": pod}})


def _service(name: str, namespace: str, labels: dict, port: int) -> dict:
    return _object("Service", name, namespace, spec={"type": "ClusterIP", "selector": labels,
                   "ports": [{"name": "service", "port": port, "targetPort": port, "protocol": "TCP"}]})


def _secret_volume(name: str) -> dict:
    return {"name": "secrets", "secret": {"secretName": name, "defaultMode": 0o444}}


def _tmp(name: str = "tmp", size: str = "32Mi") -> dict:
    return {"name": name, "emptyDir": {"medium": "Memory", "sizeLimit": size}}


def _mount(name: str, path: str, readonly: bool = False, subpath: str | None = None) -> dict:
    mount = {"name": name, "mountPath": path, "readOnly": readonly}
    if subpath is not None:
        mount["subPath"] = subpath
    return mount


def _account(name: str, namespace: str) -> dict:
    return _object("ServiceAccount", name, namespace, automountServiceAccountToken=False)


def _secret(name: str, namespace: str, files: Mapping[str, Path]) -> dict:
    return _object("Secret", name, namespace, type="Opaque", immutable=True,
                   data={key: base64.b64encode(path.read_bytes()).decode("ascii") for key, path in files.items()})


def _proxy_names(service: str, namespace: str) -> tuple[str, ...]:
    return (service, f"{service}-proxy", f"{service}-proxy.{namespace}",
            f"{service}-proxy.{namespace}.svc", f"{service}-proxy.{namespace}.svc.cluster.local", "localhost")


def _nginx(service: str, namespace: str) -> str:
    """Allow only the owning proxy's exact DNS aliases and local diagnostics."""
    configuration = local_runtime._nginx(service)
    names = (*_proxy_names(service, namespace), "127.0.0.1")
    server_line = f"        server_name {service} localhost;"
    host_line = f"        if ($host !~ ^({service}|localhost|127\\.0\\.0\\.1)$) {{ return 421; }}"
    if configuration.count(server_line) != 1 or configuration.count(host_line) != 1:
        raise ValueError("Local nginx host policy changed; review Kubernetes aliases before rendering")
    expression = "|".join(name.replace(".", r"\.") for name in names)
    return configuration.replace(server_line, "        server_name " + " ".join(names) + ";").replace(
        host_line, "        if ($host !~ ^(" + expression + ")$) { return 421; }")


def _proxy_certificates(directory: Path, namespace: str) -> None:
    """Include the Kubernetes proxy Service names in each isolated leaf certificate."""
    for service in SERVICES:
        csr, extensions = directory / f"{service}.csr", directory / f"{service}.ext"
        names = _proxy_names(service, namespace)
        extensions.write_text("basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\n"
                              "extendedKeyUsage=serverAuth\nsubjectAltName="
                              + ",".join(f"DNS:{name}" for name in names) + ",IP:127.0.0.1\n")
        extensions.chmod(0o600)
        local_runtime._openssl("req", "-new", "-key", str(directory / f"{service}.key"),
                               "-out", str(csr), "-subj", f"/CN={service}-proxy")
        certificate = directory / f"{service}.crt"
        certificate.chmod(0o600)
        local_runtime._openssl("x509", "-req", "-in", str(csr), "-CA", str(directory / "ca.crt"),
                               "-CAkey", str(directory / "ca.key"), "-set_serial", str(secrets.randbits(128) + 1),
                               "-days", "7", "-sha256", "-extfile", str(extensions), "-out", str(certificate))
        certificate.chmod(0o444)
        csr.unlink()
        extensions.unlink()


def _readiness(service: str) -> dict:
    if service in PHP_SERVICES:
        source = r'''try { require '/app/vendor/autoload.php'; $app = require '/app/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
$token = trim((string) file_get_contents('/run/secrets/health-token'));
$status = $app->make(App\Application\Foundation\Actions\InspectDependencies::class)->handle($token);
exit($status === App\Application\Foundation\Data\DependencyStatus::Ready ? 0 : 1);
} catch (Throwable) { exit(1); }'''
        command = ["php", "-r", source]
    else:
        source = ("import pathlib,urllib.request; "
                  "token=pathlib.Path('/run/secrets/health-token').read_text().strip(); "
                  "request=urllib.request.Request('http://127.0.0.1:8080/health/dependencies', "
                  "headers={'Authorization':'Bearer '+token}); "
                  "response=urllib.request.urlopen(request,timeout=5); "
                  "raise SystemExit(0 if response.status==200 else 1)")
        command = ["/opt/venv/bin/python", "-c", source]
    return {"exec": {"command": command}, "timeoutSeconds": 8, "periodSeconds": 10,
            "failureThreshold": 1, "successThreshold": 1}


def _policy(name: str, namespace: str, selector: dict, **rules: object) -> dict:
    return _object("NetworkPolicy", name, namespace, spec={"podSelector": {"matchLabels": selector},
                   "policyTypes": [key.capitalize() for key in rules], **rules})


def _network_policies(namespace: str) -> list[dict]:
    policies = [_policy("deny-by-default", namespace, {}, ingress=[], egress=[])]
    dns = {"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "kube-system"}},
           "podSelector": {"matchLabels": {"k8s-app": "kube-dns"}}}
    policies.append(_policy("cluster-dns", namespace, {}, egress=[{"to": [dns],
                    "ports": [{"port": 53, "protocol": protocol} for protocol in ("UDP", "TCP")]}]))
    clients = []
    for service in SERVICES:
        port = 9000 if service in PHP_SERVICES else 8080
        policies.append(_policy(f"{service}-application", namespace, _labels("app", service),
                        ingress=[{"from": [_peer("proxy", service)], "ports": [_port(port)]}],
                        egress=[{"to": [_peer("postgres", "postgres")], "ports": [_port(5432)]}]))
        policies.append(_policy(f"{service}-proxy", namespace, _labels("proxy", service),
                        ingress=[{"from": [_peer("probe", service)], "ports": [_port(8443)]}],
                        egress=[{"to": [_peer("app", service)], "ports": [_port(port)]}]))
        policies.append(_policy(f"{service}-migrator", namespace, _labels("migrator", service),
                        egress=[{"to": [_peer("postgres", "postgres")], "ports": [_port(5432)]}]))
        policies.append(_policy(f"{service}-probe", namespace, _labels("probe", service),
                        egress=[{"to": [_peer("proxy", service)], "ports": [_port(8443)]}]))
        clients.extend([_peer("app", service), _peer("migrator", service)])
    policies.append(_policy("postgres-private-clients", namespace, _labels("postgres", "postgres"),
                    ingress=[{"from": clients, "ports": [_port(5432)]}]))
    return policies


def prepare(root: Path, runtime: Path, images: Mapping[str, str], revision: str,
            namespace: str | None = None) -> Path:
    """Write public manifests and private Secret payloads outside the repository.

    The caller must verify/import image-imports.json into kind before applying
    resources, and must keep the complete runtime directory out of retained evidence.
    """
    root, runtime = Path(root).resolve(strict=True), Path(runtime)
    namespace = namespace or f"p01-{revision[:12]}"
    if NAMESPACE.fullmatch(namespace) is None:
        raise ValueError("Namespace must be a p01-prefixed Kubernetes DNS label")
    candidates = json.loads((root / "deploy/integration/candidates.json").read_text())
    node = candidates["node"]["reference"]
    if NODE_IMAGE.fullmatch(node) is None:
        raise ValueError("kind node must have an immutable supported Kubernetes 1.36 image digest")
    local_runtime.prepare(root, runtime, images, revision)
    try:
        compose = json.loads((runtime / "compose.json").read_text())
        secret_dir = runtime / "secrets"
        _proxy_certificates(secret_dir, namespace)
        dependency_sources = local_runtime._inputs(root, images, revision)
        dependency_imports = {name: {"source_reference": reference,
                                    "kind_reference": f"p01.local/{name}:manifest-sha256-{reference.rsplit(':', 1)[1]}"}
                              for name, reference in dependency_sources.items()}
        dependencies = {name: entry["kind_reference"] for name, entry in dependency_imports.items()}
        imports = {service: {"local_image_id": image,
                            "kind_reference": f"p01.local/{service}:sha256-{image.split(':')[1]}"}
                   for service, image in images.items()}
        resources, migrations, private_secrets = [], [], []

        for service in SERVICES:
            source = compose["services"][service]
            image = imports[service]["kind_reference"]
            fields = {entry["target"]: secret_dir / entry["source"] for entry in source["secrets"]}
            private_secrets.append(_secret(f"{service}-runtime", namespace, fields))
            private_secrets.append(_secret(f"{service}-tls", namespace,
                                  {"tls.crt": secret_dir / f"{service}.crt", "tls.key": secret_dir / f"{service}.key"}))
            private_secrets.append(_secret(f"{service}-migration", namespace,
                                  {"db-password": secret_dir / f"{service}-migrator-password", "ca.crt": secret_dir / "ca.crt"}))
            app = _container(service, image, "512Mi" if service in PHP_SERVICES else "256Mi")
            app["env"] = [{"name": key, "value": value} for key, value in source["environment"].items()]
            app["volumeMounts"] = [_mount("secrets", "/run/secrets", True), _mount("tmp", "/tmp")]
            app["readinessProbe"] = _readiness(service)
            port = 9000 if service in PHP_SERVICES else 8080
            app["livenessProbe"] = {"tcpSocket": {"port": port}, "periodSeconds": 10, "timeoutSeconds": 2}
            app["startupProbe"] = {"tcpSocket": {"port": port}, "periodSeconds": 2, "failureThreshold": 60}
            volumes = [_secret_volume(f"{service}-runtime"), _tmp()]
            if service in PHP_SERVICES:
                app["args"] = source["command"]
                volumes.extend([_tmp("storage"), _tmp("config-cache", "16Mi")])
                app["volumeMounts"].extend([_mount("storage", "/app/storage"), _mount("config-cache", "/app/bootstrap/cache")])
            else:
                app["command"] = source["entrypoint"]
            app_labels = _labels("app", service)
            resources.extend([_account(service, namespace), _deployment(service, namespace, app_labels, _pod(service, [app], volumes)),
                              _service(service, namespace, app_labels, port)])

            proxy_name = f"{service}-proxy"
            proxy = _container(proxy_name, dependencies["nginx"], "128Mi")
            proxy.update(command=["/usr/sbin/nginx"], args=["-g", "daemon off;"],
                         volumeMounts=[_mount("secrets", "/run/secrets", True), _mount("tmp", "/tmp"),
                                       _mount("config", "/etc/nginx/nginx.conf", True, "nginx.conf")],
                         readinessProbe={"tcpSocket": {"port": 8443}, "periodSeconds": 5, "timeoutSeconds": 2},
                         livenessProbe={"tcpSocket": {"port": 8443}, "periodSeconds": 10, "timeoutSeconds": 2})
            proxy_volumes = [_secret_volume(f"{service}-tls"), _tmp(),
                             {"name": "config", "configMap": {"name": proxy_name}}]
            proxy_pod = _pod(proxy_name, [proxy], proxy_volumes)
            if service in PHP_SERVICES:
                proxy_volumes.append({"name": "public", "emptyDir": {"sizeLimit": "64Mi"}})
                proxy["volumeMounts"].append(_mount("public", "/srv/public", True))
                copy = _container("copy-public-assets", image)
                copy.update(command=["/bin/sh", "-ec", "cp -R /app/public/. /srv/public/"],
                            volumeMounts=[_mount("public", "/srv/public")])
                proxy_pod["initContainers"] = [copy]
            proxy_labels = _labels("proxy", service)
            resources.extend([_account(proxy_name, namespace),
                              _object("ConfigMap", proxy_name, namespace, data={"nginx.conf": _nginx(service, namespace)}),
                              _deployment(proxy_name, namespace, proxy_labels, proxy_pod),
                              _service(proxy_name, namespace, proxy_labels, 8443)])

            migrator_name = f"{service}-migrator"
            migration = _container("migrate", dependencies["postgres"])
            migration.update(command=["/bin/sh", "-ec",
                'export PGPASSWORD="$(cat /run/secrets/db-password)"; '
                f'exec psql -X --quiet --set=ON_ERROR_STOP=1 --set=owner={service}_owner '
                f'--set=runtime={service}_runtime "host=postgres port=5432 dbname={service} '
                f'user={service}_migrator sslmode=verify-full sslrootcert=/run/secrets/ca.crt connect_timeout=3" '
                '--file=/opt/foundation/migrate.sql'],
                volumeMounts=[_mount("secrets", "/run/secrets", True),
                              _mount("migration", "/opt/foundation/migrate.sql", True, "migrate.sql")])
            migration_pod = _pod(migrator_name, [migration], [_secret_volume(f"{service}-migration"),
                                 {"name": "migration", "configMap": {"name": "postgres-scripts"}}])
            migration_pod["restartPolicy"] = "Never"
            resources.append(_account(migrator_name, namespace))
            migrations.append(_object("Job", migrator_name, namespace, spec={"backoffLimit": 0, "activeDeadlineSeconds": 120,
                              "template": {"metadata": {"labels": _labels("migrator", service)}, "spec": migration_pod}}))

        pg_source = compose["services"]["postgres"]
        private_secrets.append(_secret("postgres-bootstrap", namespace,
                              {entry["target"]: secret_dir / entry["source"] for entry in pg_source["secrets"]}))
        scripts = {name: (root / "deploy/dependencies/postgres" / name).read_text()
                   for name in ("entrypoint.sh", "initialize.sh", "migrate.sql")}
        resources.append(_object("ConfigMap", "postgres-scripts", namespace, data=scripts))
        resources.append(_object("PersistentVolumeClaim", "postgres-data", namespace,
                         spec={"accessModes": ["ReadWriteOnce"], "resources": {"requests": {"storage": "1Gi"}}}))
        postgres = _container("postgres", dependencies["postgres"], "512Mi")
        postgres["securityContext"].update(runAsUser=0, runAsGroup=0, runAsNonRoot=False,
                                           capabilities={"drop": ["ALL"], "add": pg_source["cap_add"]})
        postgres.update(command=["/bin/bash", "/opt/foundation/entrypoint.sh"], args=["postgres"],
                        ports=[{"containerPort": 5432}],
                        volumeMounts=[_mount("secrets", "/run/secrets", True), _mount("tmp", "/tmp"),
                                      _mount("socket", "/var/run/postgresql"), _mount("data", "/var/lib/postgresql"),
                                      _mount("scripts", "/opt/foundation", True),
                                      _mount("scripts", "/docker-entrypoint-initdb.d/10-private-identities.sh", True, "initialize.sh")],
                        startupProbe={"tcpSocket": {"port": 5432}, "periodSeconds": 2, "failureThreshold": 60},
                        readinessProbe={"tcpSocket": {"port": 5432}, "periodSeconds": 5, "timeoutSeconds": 2},
                        livenessProbe={"tcpSocket": {"port": 5432}, "periodSeconds": 10, "timeoutSeconds": 2})
        postgres_pod = _pod("postgres", [postgres], [_secret_volume("postgres-bootstrap"), _tmp("tmp", "64Mi"),
                            _tmp("socket", "16Mi"), {"name": "data", "persistentVolumeClaim": {"claimName": "postgres-data"}},
                            {"name": "scripts", "configMap": {"name": "postgres-scripts", "defaultMode": 0o555}}])
        postgres_pod["securityContext"] = {"runAsUser": 0, "runAsGroup": 0,
                                            "seccompProfile": {"type": "RuntimeDefault"}}
        pg_labels = _labels("postgres", "postgres")
        resources.extend([_account("postgres", namespace), _deployment("postgres", namespace, pg_labels, postgres_pod),
                          _service("postgres", namespace, pg_labels, 5432), *_network_policies(namespace)])

        _write(runtime / "namespace.json", {"apiVersion": "v1", "kind": "Namespace", "metadata": {
            "name": namespace, "labels": {"app.kubernetes.io/part-of": "p01-foundation"}}})
        _write(runtime / "resources.json", _list(resources))
        _write(runtime / "migrations.json", _list(migrations))
        _write(runtime / "secrets.json", _list(private_secrets))
        _write(runtime / "image-imports.json", {"applications": imports, "dependencies": dependency_imports})
        _write(runtime / "kind.json", {"kind": "Cluster", "apiVersion": "kind.x-k8s.io/v1alpha4",
               "networking": {"disableDefaultCNI": True, "apiServerAddress": "127.0.0.1"},
               "nodes": [{"role": "control-plane", "image": node}, {"role": "worker", "image": node}]})
        _write(runtime / "fixture.json", {"scope": "synthetic-kind-foundation", "source_revision": revision,
               "namespace": namespace, "native_operations_enabled": False, "rendered_only": True,
               "readiness_scope": "foundation_dependencies; product /health/ready remains 503",
               "secrets_must_not_be_retained": True})
        return runtime / "resources.json"
    except BaseException:
        shutil.rmtree(runtime)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--namespace")
    args = parser.parse_args()
    try:
        print(prepare(args.workspace, args.runtime, json.loads(args.images.read_text()), args.source_revision, args.namespace))
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        parser.exit(1, f"Cannot prepare P01 Kubernetes fixture: {error}\n")


if __name__ == "__main__":
    main()
