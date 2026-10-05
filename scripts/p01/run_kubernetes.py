"""Measure an isolated kind/Cilium foundation with synthetic credentials only."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tarfile
import urllib.request

from kubernetes_runtime import prepare
from local_runtime import PHP_SERVICES, SERVICES
from run_local import Campaign, digest


NETWORK_PROBE = """import json,socket,sys
request=json.load(sys.stdin)
try:
    with socket.create_connection((request['host'],request['port']),timeout=3):
        result={'outcome':'connected'}
except TimeoutError:
    result={'outcome':'timeout'}
except OSError as error:
    result={'outcome':'error','error_type':type(error).__name__}
print(json.dumps(result))
"""

HTTP_PROBE = """import json,pathlib,ssl,sys,urllib.request,urllib.error
request=json.load(sys.stdin)
headers={}
if request.get('identity')=='valid':
    headers['Authorization']='Bearer '+pathlib.Path('/run/secrets/health-token').read_text().strip()
elif request.get('identity')=='invalid':
    headers['Authorization']='Bearer invalid-synthetic-token'
if request.get('host'):
    headers['Host']=request['host']
context=ssl.create_default_context(cafile='/run/secrets/ca.crt') if request.get('trust',True) else ssl.create_default_context()
message=urllib.request.Request(request['url'],headers=headers)
try:
    try:
        response=urllib.request.urlopen(message,context=context,timeout=8)
    except urllib.error.HTTPError as error:
        response=error
    with response:
        print(json.dumps({'status':response.status,'body':response.read(65536).decode(),
            'cache_control':response.headers.get('Cache-Control','')}))
except urllib.error.URLError as error:
    if isinstance(error.reason,ssl.SSLCertVerificationError):
        print(json.dumps({'tls_verification_failed':True}))
    else:
        raise
"""


def image_identity(raw: bytes, image: str, service: str, revision: str) -> dict:
    """Validate only selected public image fields, without retaining its environment."""
    decoder, fields, remaining = json.JSONDecoder(), [], raw.decode().strip()
    while remaining:
        value, end = decoder.raw_decode(remaining)
        fields.append(value)
        remaining = remaining[end:].lstrip()
    if len(fields) != 4 or not isinstance(fields[3], dict):
        raise ValueError("Malformed image identity")
    if fields[:3] != [image, "linux", "amd64"] or fields[3].get("org.opencontainers.image.revision") != revision or fields[3].get("io.product.component") != service:
        raise ValueError("Application image source, owner or platform mismatch")
    return {"image_id": fields[0], "os": fields[1], "architecture": fields[2], "labels": fields[3]}


class KubernetesCampaign(Campaign):
    def __init__(self, root: Path, output: Path, revision: str):
        super().__init__(root, output, revision)
        self.cluster = "p01-" + revision[:12] + "-" + secrets.token_hex(4)
        self.namespace = self.cluster
        self.kubeconfig = self.runtime.parent / "kubeconfig"
        self.tools = self.runtime.parent / "tools"
        self.tools.mkdir(mode=0o700)
        self.cluster_attempted = False
        self.report["scope"] = "Synthetic isolated kind/Cilium foundation; no product readiness or native effects"
        self.report["cluster"] = self.cluster
        self.report["namespace"] = self.namespace
        self.report["tool_artifacts"] = []

    def k(self, *arguments: str, namespace: str | None = None) -> list[str]:
        return [str(self.tools / "kubectl"), "--kubeconfig", str(self.kubeconfig),
                "--namespace", namespace or self.namespace, *arguments]

    def download(self, name: str, url: str, checksum_url: str, expected: str | None = None) -> Path:
        for value in (url, checksum_url):
            if not value.startswith("https://"):
                raise ValueError("Tool artifacts must use HTTPS")
        if expected is None:
            with urllib.request.urlopen(checksum_url, timeout=60) as response:
                advertised = response.read(4096).decode().split()[0]
        else:
            advertised = expected
        self.check(name + "-published-checksum", bool(re.fullmatch(r"[0-9a-f]{64}", advertised)) and (expected is None or advertised == expected))
        path = self.tools / name
        with urllib.request.urlopen(url, timeout=60) as response, path.open("wb") as output:
            shutil.copyfileobj(response, output)
        actual = digest(path.read_bytes())
        self.check(name + "-artifact-integrity", actual == advertised)
        self.report["tool_artifacts"].append({"name": name, "url": url, "checksum_url": checksum_url, "published_sha256": advertised, "actual_sha256": actual, "bytes": path.stat().st_size})
        path.chmod(0o700)
        self.save()
        return path

    def install_tools(self, candidates: dict) -> None:
        kind = candidates["kind"]
        self.download("kind", kind["binary"], kind["checksum_source"], kind["sha256"])
        observed = self.command("kind-version", [str(self.tools / "kind"), "version"]).decode()
        self.check("exact-kind-version", observed.split()[:2] == ["kind", kind["version"]])
        version = candidates["node"]["version"]
        binary = f"https://dl.k8s.io/release/{version}/bin/linux/amd64/kubectl"
        self.download("kubectl", binary, binary + ".sha256")
        client = json.loads(self.command("kubectl-version", [str(self.tools / "kubectl"), "version", "--client", "-o", "json"]))
        self.check("exact-kubectl-version", client["clientVersion"]["gitVersion"] == version)
        helm = candidates["helm"]
        archive = self.download("helm.tar.gz", helm["binary"], helm["checksum_source"], helm["sha256"])
        with tarfile.open(archive) as package:
            member = package.getmember("linux-amd64/helm")
            if not member.isfile():
                raise ValueError("Helm artifact does not contain a regular executable")
            handle = package.extractfile(member)
            if handle is None:
                raise ValueError("Helm executable is absent")
            with handle, (self.tools / "helm").open("wb") as executable:
                shutil.copyfileobj(handle, executable)
        (self.tools / "helm").chmod(0o700)
        observed = self.command("helm-version", [str(self.tools / "helm"), "version", "--template", "{{.Version}}"])
        self.check("exact-helm-version", observed.decode().strip() == helm["version"])

    def build_images(self, images_path: Path | None) -> dict[str, str]:
        if images_path is not None:
            images = json.loads(images_path.read_text())
        else:
            def build(service):
                destination = self.output / "images" / service
                argv = [sys.executable, str(self.root / "scripts/p01/run_images.py"), "--component", service,
                        "--output", str(destination), "--source-revision", self.revision]
                try:
                    result = subprocess.run(argv, cwd=self.root, capture_output=True, timeout=1200)
                except subprocess.TimeoutExpired as error:
                    (self.output / f"{service}-build-runner.log").write_bytes((error.stdout or b"") + (error.stderr or b"") + b"\nImage build timed out.\n")
                    raise RuntimeError(f"{service} image build timed out") from error
                (self.output / f"{service}-build-runner.log").write_bytes(result.stdout + result.stderr)
                if result.returncode:
                    raise RuntimeError(f"{service} image verification failed")
                report = json.loads((destination / "report.json").read_text())
                if report["result"] != "PASSED":
                    raise RuntimeError(f"{service} image evidence did not pass")
                return service, report["image"]["id"]
            with ThreadPoolExecutor(max_workers=3) as pool:
                images = dict(pool.map(build, SERVICES))
        self.check("exact-seven-owned-images", set(images) == set(SERVICES) and all(re.fullmatch(r"sha256:[0-9a-f]{64}", image) for image in images.values()))
        identities = {}
        for service, image in images.items():
            raw = self.command("application-image-identity", ["docker", "image", "inspect", "--format",
                               "{{json .Id}} {{json .Os}} {{json .Architecture}} {{json .Config.Labels}}", image])
            identities[service] = image_identity(raw, image, service, self.revision)
        self.report["application_images"] = identities
        return images

    def install_cilium(self, candidates: dict) -> None:
        helm = str(self.tools / "helm")
        selection = candidates["cilium"]
        charts = self.runtime.parent / "charts"
        charts.mkdir()
        self.command("fetch-cilium-chart", [helm, "pull", selection["chart"], "--version", selection["version"], "--destination", str(charts)], timeout=180)
        command = self.report["commands"][-1]
        pull_output = b"\n".join((self.output / command[stream]["path"]).read_bytes() for stream in ("stdout", "stderr"))
        digests = set(re.findall(rb"Digest:\s+(sha256:[a-f0-9]{64})", pull_output))
        self.check("cilium-chart-oci-digest-observed", len(digests) == 1)
        oci_digest = next(iter(digests)).decode()
        chart = charts / f"cilium-{selection['version']}.tgz"
        self.check("cilium-chart-present", chart.is_file())
        actual = digest(chart.read_bytes())
        if "chart_sha256" in selection:
            self.check("cilium-chart-replay-archive-matches", selection["chart_sha256"] == actual)
        if "chart_oci_digest" in selection:
            self.check("cilium-chart-replay-oci-matches", selection["chart_oci_digest"] == oci_digest)
        self.report["cilium_chart"] = {"reference": selection["chart"], "version": selection["version"], "archive_sha256": actual, "oci_digest": oci_digest,
            "mode": "locked_replay" if "chart_sha256" in selection and "chart_oci_digest" in selection else "first_observed_candidate"}
        (self.output / "cilium-observed-lock.json").write_text(json.dumps(self.report["cilium_chart"], indent=2) + "\n")
        values = self.root / "deploy/integration/cilium-values.json"
        rendered = self.command("render-cilium-chart", [helm, "template", "cilium", str(chart), "--namespace", "kube-system", "--values", str(values)])
        images = sorted(set(re.findall(r"^\s*image:\s*[\"']?([^\s\"']+)", rendered.decode(), re.MULTILINE)))
        self.check("cilium-rendered-images-immutable", bool(images) and all(re.search(r"@sha256:[a-f0-9]{64}$", image) for image in images))
        self.report["cilium_rendered_images"] = images
        self.command("install-cilium", [helm, "upgrade", "--install", "cilium", str(chart), "--kubeconfig", str(self.kubeconfig), "--namespace", "kube-system", "--values", str(values), "--wait", "--timeout", "300s"], timeout=330)
        self.command("cilium-daemonset-ready", self.k("rollout", "status", "daemonset/cilium", "--timeout=240s", namespace="kube-system"), timeout=260)
        self.command("cilium-status", self.k("exec", "daemonset/cilium", "-c", "cilium-agent", "--", "cilium-dbg", "status", "--brief", namespace="kube-system"))
        nodes = json.loads(self.command("node-inventory", self.k("get", "nodes", "-o", "json")))
        self.check("exact-kubernetes-server-version", all(node["status"]["nodeInfo"]["kubeletVersion"] == candidates["node"]["version"] for node in nodes["items"]))
        cni = json.loads(self.command("cilium-pod-inventory", self.k("get", "pods", "-l", "k8s-app=cilium", "-o", "json", namespace="kube-system")))
        self.check("cilium-installed-image-identities", len(cni["items"]) == 2 and all(
            status.get("ready") and status.get("imageID") for pod in cni["items"] for status in pod["status"]["containerStatuses"]))

    def apply(self, name: str, path: Path) -> None:
        self.command(name, self.k("apply", "-f", str(path)))

    def exec(self, service: str, argv: list[str], *, data: bytes | None = None, expected: int = 0, timeout: int = 30, role: str = "app") -> bytes:
        target = service + "-probe" if role == "probe" else service
        container = "probe" if role == "probe" else service
        return self.command(f"{service}-{role}-exec", self.k("exec", "-i", "deployment/" + target, "-c", container, "--", *argv), data=data, expected=expected, timeout=timeout)

    def sql(self, service: str, sql: str, *, identity: str = "runtime", database: str | None = None, expected: int = 0, sslmode: str = "verify-full", bad_password: bool = False) -> bytes:
        password = "invalid-synthetic-password" if bad_password else f"$(cat /run/secrets/{service}-{identity}-password)"
        # Loopback isolates the credential/SQL negative tests from Cilium tests below.
        # host still names the verified certificate; hostaddr selects only loopback.
        command = f'export PGPASSWORD="{password}"; exec psql -X -qAt -v ON_ERROR_STOP=1 "host=postgres hostaddr=127.0.0.1 port=5432 dbname={database or service} user={service}_{identity} sslmode={sslmode} sslrootcert=/run/secrets/ca.crt connect_timeout=2"'
        return self.exec("postgres", ["sh", "-ec", command], data=sql.encode(), expected=expected)

    def admin(self, sql: str) -> bytes:
        return self.exec("postgres", ["gosu", "postgres", "psql", "-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-d", "postgres"], data=sql.encode())

    def http(self, service: str, path: str, *, identity: str | None = None, trust: bool = True, host: str | None = None) -> dict:
        data = json.dumps({"url": f"https://{service}-proxy:8443" + path, "identity": identity, "trust": trust, "host": host}).encode()
        return json.loads(self.exec(service, ["/opt/venv/bin/python", "-I", "-c", HTTP_PROBE], data=data, role="probe"))

    def health(self, service: str, status: int, identity: str | None = "valid") -> None:
        result = self.http(service, "/health/dependencies", identity=identity)
        body = json.loads(result.get("body", "{}"))
        expected = {"service": service, "status": {200: "ready", 401: "unauthorized", 503: "not_ready"}[status], "scope": "foundation_dependencies"}
        if service not in PHP_SERVICES:
            expected["native_operations_enabled"] = False
        if status == 503:
            expected["reason"] = "dependency_unavailable" if service in PHP_SERVICES else "dependencies_unavailable"
        self.check("dependency-http-contract", result.get("status") == status and body == expected and "no-store" in result.get("cache_control", ""), {"service": service, "identity": identity, "response": result})

    def make_probes(self, imports: dict) -> None:
        resources = []
        for service in SERVICES:
            name = service + "-probe"
            labels = {"app.kubernetes.io/part-of": "p01-foundation", "p01.role": "probe", "p01.service": service}
            resources.append({"apiVersion": "v1", "kind": "ServiceAccount", "metadata": {"name": name, "namespace": self.namespace}, "automountServiceAccountToken": False})
            pod = {"serviceAccountName": name, "automountServiceAccountToken": False, "enableServiceLinks": False,
                   "securityContext": {"runAsNonRoot": True, "runAsUser": 10001, "runAsGroup": 10001, "seccompProfile": {"type": "RuntimeDefault"}},
                   "containers": [{"name": "probe", "image": imports["applications"]["planning"]["kind_reference"], "imagePullPolicy": "Never",
                       "command": ["/opt/venv/bin/python", "-I", "-c", "import time; time.sleep(2400)"],
                       "securityContext": {"readOnlyRootFilesystem": True, "allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}},
                       "resources": {"requests": {"cpu": "10m", "memory": "32Mi"}, "limits": {"cpu": "250m", "memory": "128Mi"}},
                       "volumeMounts": [{"name": "health", "mountPath": "/run/secrets", "readOnly": True}]}],
                   "volumes": [{"name": "health", "secret": {"secretName": service + "-runtime", "defaultMode": 0o444,
                       "items": [{"key": key, "path": key} for key in ("ca.crt", "health-token")]}}]}
            resources.append({"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": name, "namespace": self.namespace},
                              "spec": {"replicas": 1, "selector": {"matchLabels": labels}, "template": {"metadata": {"labels": labels}, "spec": pod}}})
        path = self.runtime / "probes.json"
        path.write_text(json.dumps({"apiVersion": "v1", "kind": "List", "items": resources}))
        self.apply("install-private-health-probes", path)
        for service in SERVICES:
            self.command("health-probe-ready", self.k("rollout", "status", "deployment/" + service + "-probe", "--timeout=120s"), timeout=140)

    def pod_ip(self, role: str, service: str) -> str:
        raw = self.command("target-pod-address", self.k("get", "pods", "-l", f"p01.role={role},p01.service={service}", "-o", "json"))
        pods = json.loads(raw)["items"]
        active = [pod for pod in pods if not pod["metadata"].get("deletionTimestamp") and pod["status"].get("podIP")]
        self.check("one-active-policy-target", len(active) == 1, {"role": role, "service": service})
        return active[0]["status"]["podIP"]

    def network_check(self, source: str, target: str, port: int, allowed: bool, *, role: str = "probe") -> None:
        result = json.loads(self.exec(source, ["/opt/venv/bin/python", "-I", "-c", NETWORK_PROBE],
                                     data=json.dumps({"host": target, "port": port}).encode(), role=role))
        self.check("cilium-allow" if allowed else "cilium-deny", result == {"outcome": "connected" if allowed else "timeout"},
                   {"source_service": source, "source_role": role, "target_ip": target, "port": port, "observed": result})

    def readiness(self, service: str, ready: bool) -> None:
        deployment = next(item for item in self.resources["items"] if item["kind"] == "Deployment" and item["metadata"]["name"] == service)
        argv = deployment["spec"]["template"]["spec"]["containers"][0]["readinessProbe"]["exec"]["command"]
        self.exec(service, argv, expected=0 if ready else 1)
        self.check("direct-application-dependency-readiness", True, {"service": service, "ready": ready})

    def run(self, images_path: Path | None) -> None:
        self.check("full-source-revision", bool(re.fullmatch(r"[0-9a-f]{40}", self.revision)))
        measured = self.command("source-revision", ["git", "rev-parse", "HEAD"]).decode().strip()
        self.check("exact-source-revision", measured == self.revision)
        changed = self.command("source-clean", ["git", "status", "--porcelain", "--untracked-files=all", "--", "scripts/p01", "deploy", "services", "apps/console", ".github/workflows/p01-kubernetes-integration.yml"])
        self.check("no-modified-or-untracked-inputs", not changed.strip())
        self.report["installation_source_sha256"] = {str(path.relative_to(self.root)): digest(path.read_bytes())
            for folder in ("scripts/p01", "deploy/integration", "deploy/dependencies") for path in sorted((self.root / folder).rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts}
        candidates = json.loads((self.root / "deploy/integration/candidates.json").read_text())
        self.report["cluster_candidates"] = candidates
        self.install_tools(candidates)
        images = self.build_images(images_path)
        manifest = prepare(self.root, self.runtime, images, self.revision, self.namespace)
        self.resources = json.loads(manifest.read_text())
        for filename in ("resources.json", "migrations.json", "namespace.json", "kind.json", "image-imports.json", "fixture.json"):
            shutil.copyfile(self.runtime / filename, self.output / filename)
        imports = json.loads((self.runtime / "image-imports.json").read_text())
        node_reference = candidates["node"]["reference"]
        self.command("pull-pinned-kind-node", ["docker", "pull", "--platform", "linux/amd64", node_reference], timeout=180)
        node_digests = json.loads(self.command("kind-node-registry-identities", ["docker", "image", "inspect", "--format", "{{json .RepoDigests}}", node_reference]))
        self.check("kind-node-registry-digest-matches", any(value.endswith("@" + node_reference.split("@", 1)[1]) for value in node_digests))
        self.report["kind_node_repo_digests"] = node_digests
        self.cluster_attempted = True
        self.command("create-isolated-kind", [str(self.tools / "kind"), "create", "cluster", "--name", self.cluster,
                     "--config", str(self.runtime / "kind.json"), "--kubeconfig", str(self.kubeconfig), "--wait", "0s"], timeout=240)
        self.kubeconfig.chmod(0o600)
        self.install_cilium(candidates)
        for service, item in imports["applications"].items():
            self.command("tag-owned-kind-image", ["docker", "tag", item["local_image_id"], item["kind_reference"]])
            self.command("import-owned-kind-image", [str(self.tools / "kind"), "load", "docker-image", "--name", self.cluster, item["kind_reference"]], timeout=180)
        imported = {item["kind_reference"]: item["local_image_id"] for item in imports["applications"].values()}
        self.report["dependency_images"] = {}
        for name, item in imports["dependencies"].items():
            reference = item["source_reference"]
            self.command("pull-locked-" + name, ["docker", "pull", "--platform", "linux/amd64", reference], timeout=180)
            image_id = json.loads(self.command("locked-image-configuration-id", ["docker", "image", "inspect", "--format", "{{json .Id}}", reference]))
            repo_digests = json.loads(self.command("locked-image-registry-identities", ["docker", "image", "inspect", "--format", "{{json .RepoDigests}}", reference]))
            self.check("dependency-registry-digest-matches", any(value.endswith("@" + reference.split("@", 1)[1]) for value in repo_digests))
            self.report["dependency_images"][name] = {"source_reference": reference, "kind_reference": item["kind_reference"], "local_image_id": image_id, "repo_digests": repo_digests}
            imported[item["kind_reference"]] = image_id
            self.command("tag-locked-kind-image", ["docker", "tag", image_id, item["kind_reference"]])
            self.command("import-locked-" + name, [str(self.tools / "kind"), "load", "docker-image", "--name", self.cluster, item["kind_reference"]], timeout=180)
        for node in (self.cluster + "-control-plane", self.cluster + "-worker"):
            inventory = json.loads(self.command("kind-node-image-inventory", ["docker", "exec", node, "crictl", "images", "--output", "json"]))
            observed = {tag: image["id"] for image in inventory["images"] for tag in image.get("repoTags", [])}
            self.check("imported-images-match-docker-configuration-ids", all(observed.get(tag) == identity for tag, identity in imported.items()), {"node": node, "expected": imported})
        self.apply("install-namespace", self.runtime / "namespace.json")
        self.apply("install-private-credentials", self.runtime / "secrets.json")
        self.apply("install-foundation-resources", manifest)
        self.command("postgres-ready", self.k("rollout", "status", "deployment/postgres", "--timeout=180s"), timeout=200)
        self.apply("apply-owned-migrations", self.runtime / "migrations.json")
        for service in SERVICES:
            self.command("owned-migration-complete", self.k("wait", "--for=condition=complete", "job/" + service + "-migrator", "--timeout=120s"), timeout=140)
            self.command("application-ready", self.k("rollout", "status", "deployment/" + service, "--timeout=180s"), timeout=200)
            self.command("proxy-ready", self.k("rollout", "status", "deployment/" + service + "-proxy", "--timeout=120s"), timeout=140)
        self.make_probes(imports)
        baseline = {}
        for service in SERVICES:
            self.health(service, 200)
            self.health(service, 401, None)
            self.health(service, 401, "invalid")
            self.check("process-liveness", self.http(service, "/health/live").get("status") == 200, service)
            self.check("product-readiness-unavailable", self.http(service, "/health/ready").get("status") == 503, service)
            self.check("untrusted-ingress-ca-denied", self.http(service, "/health/live", trust=False) == {"tls_verification_failed": True}, service)
            self.check("foreign-host-denied", self.http(service, "/health/live", host="foreign.invalid").get("status") == 421, service)
            for path in ("/.env", "/composer.json", "/config/app.php"):
                self.check("source-outside-public-root", self.http(service, path).get("status") == 404, {"service": service, "path": path})
            baseline[service] = digest(self.sql(service, "SELECT tenant_id,record_id,payload FROM app.foundation_records ORDER BY tenant_id,record_id;"))
            self.sql(service, "BEGIN; INSERT INTO app.foundation_records VALUES ('tenant_a','runtime-write','synthetic'); ROLLBACK;")
            for sql in ("CREATE TABLE app.forbidden(id integer);", "UPDATE app.foundation_schema SET version=2;", f"SET ROLE {service}_owner;"):
                self.sql(service, sql, expected=3)
            self.sql(service, "SELECT 1;", database="catalogue" if service != "catalogue" else "governance", expected=2)
            self.sql(service, "SELECT 1;", sslmode="disable", expected=2)
            self.sql(service, "SELECT 1;", bad_password=True, expected=2)
        self.report["fixture_data_sha256"] = baseline
        pg_ip = self.pod_ip("postgres", "postgres")
        for service in SERVICES:
            foreign = "catalogue" if service != "catalogue" else "governance"
            self.network_check(service, self.pod_ip("proxy", service), 8443, True)
            self.network_check(service, self.pod_ip("proxy", foreign), 8443, False)
            self.network_check(service, pg_ip, 5432, False)
        self.network_check("planning", pg_ip, 5432, True, role="app")
        self.network_check("planning", self.pod_ip("app", "governance"), 9000, False, role="app")
        self.admin("ALTER ROLE governance_runtime NOLOGIN;")
        self.readiness("governance", False)
        self.admin("ALTER ROLE governance_runtime LOGIN;")
        self.readiness("governance", True)
        self.command("stop-database", self.k("scale", "deployment/postgres", "--replicas=0"))
        self.command("database-stopped", self.k("wait", "--for=delete", "pod", "-l", "p01.role=postgres", "--timeout=90s"), timeout=110)
        for service in SERVICES:
            self.readiness(service, False)
            if service in PHP_SERVICES:
                self.exec(service, ["php", "-r", "$s=fsockopen('127.0.0.1',9000,$n,$e,2); if (!$s) {exit(1);} fclose($s);"])
            else:
                self.exec(service, ["/opt/venv/bin/python", "-I", "-c", "import urllib.request; assert urllib.request.urlopen('http://127.0.0.1:8080/health/live',timeout=3).status==200"])
        self.command("restart-database", self.k("scale", "deployment/postgres", "--replicas=1"))
        self.command("restarted-database-ready", self.k("rollout", "status", "deployment/postgres", "--timeout=180s"), timeout=200)
        for service in SERVICES:
            self.command("application-recovered", self.k("rollout", "status", "deployment/" + service, "--timeout=120s"), timeout=140)
            self.health(service, 200)
            actual = digest(self.sql(service, "SELECT tenant_id,record_id,payload FROM app.foundation_records ORDER BY tenant_id,record_id;"))
            self.check("restart-preserves-fixture-data", actual == baseline[service], {"service": service, "sha256": actual})
        self.command("installed-pod-inventory", self.k("get", "pods", "-o", "json"))
        self.command("installed-network-policies", self.k("get", "networkpolicies", "-o", "json"))
        self.report["result"] = "PASS"
        self.report["limits"] = ["Synthetic diagnostic identities and data only; no OIDC or delegated product authority.",
            "Default-deny Cilium pod traffic and owned allow paths measured; no production cluster or multi-site security qualification.",
            "Persistent PostgreSQL deployment restart measured; full application/configuration restore, broker, Temporal, evidence storage and operating acceptance remain unmeasured.",
            "Product readiness remains unavailable; no task consumption, native platform endpoints or effects."]
        self.save()

    def cleanup(self, keep: bool) -> None:
        if self.cluster_attempted:
            for service in (*SERVICES, "postgres", *(s + "-proxy" for s in SERVICES)):
                try:
                    self.command("container-logs-" + service, self.k("logs", "deployment/" + service, "--all-containers=true", "--tail=200"), expected=None, timeout=20)
                except Exception:
                    self.report.setdefault("log_capture_failures", []).append(service)
            for service in SERVICES:
                try:
                    self.command("migration-logs-" + service, self.k("logs", "job/" + service + "-migrator", "-c", "migrate", "--tail=100"), expected=None, timeout=20)
                except Exception:
                    self.report.setdefault("log_capture_failures", []).append(service + "-migrator")
            if not keep:
                try:
                    self.command("delete-owned-kind-cluster", [str(self.tools / "kind"), "delete", "cluster", "--name", self.cluster], timeout=180)
                    self.report["cleanup_complete"] = True
                except Exception:
                    self.report.update(result="FAIL", cleanup_complete=False, cleanup_runtime_preserved=str(self.runtime))
                    self.save()
                    raise
        if not keep:
            shutil.rmtree(self.runtime.parent)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--images", type=Path)
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    campaign = KubernetesCampaign(args.workspace.resolve(), args.output.resolve(), args.source_revision)
    try:
        campaign.run(args.images)
    except Exception as error:
        campaign.report.update(result="FAIL", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        try:
            campaign.cleanup(args.keep)
        finally:
            campaign.save()


if __name__ == "__main__":
    main()
