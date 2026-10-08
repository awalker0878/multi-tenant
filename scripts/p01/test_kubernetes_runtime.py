"""Check the generated trust boundaries; these are not Kubernetes observations."""
import base64
import json
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import unittest

import kubernetes_runtime as runtime


ROOT = Path(__file__).resolve().parents[2]
REVISION = "1" * 40
IMAGES = {name: "sha256:" + f"{index:064x}" for index, name in enumerate(runtime.SERVICES, 1)}


def matches(selector, labels):
    return all(labels.get(key) == value for key, value in selector.get("matchLabels", {}).items())


def allows(policies, source, destination, port):
    """Evaluate the namespace-local TCP subset independently for boundary assertions."""
    def direction_allowed(direction, subject, peer):
        selected = [policy["spec"] for policy in policies
                    if direction.capitalize() in policy["spec"]["policyTypes"]
                    and matches(policy["spec"]["podSelector"], subject)]
        if not selected:
            return True
        for policy in selected:
            for rule in policy.get(direction, []):
                if not any(item.get("protocol", "TCP") == "TCP" and item["port"] == port
                           for item in rule.get("ports", [])):
                    continue
                for candidate in rule.get("from" if direction == "ingress" else "to", []):
                    # Namespace-qualified DNS traffic is outside this local-peer test.
                    if "namespaceSelector" not in candidate and matches(candidate.get("podSelector", {}), peer):
                        return True
        return False
    return direction_allowed("egress", source, destination) and direction_allowed("ingress", destination, source)


class KubernetesBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="p01-kube-tests-")
        cls.directory = Path(cls.temporary.name) / "runtime"
        cls.path = runtime.prepare(ROOT, cls.directory, IMAGES, REVISION, "p01-test")
        cls.resources = json.loads(cls.path.read_text())["items"]
        cls.migrations = json.loads((cls.directory / "migrations.json").read_text())["items"]
        cls.secrets = json.loads((cls.directory / "secrets.json").read_text())["items"]
        cls.policies = [item for item in cls.resources if item["kind"] == "NetworkPolicy"]
        cls.deployments = {item["metadata"]["name"]: item["spec"]["template"]["spec"]
                           for item in cls.resources if item["kind"] == "Deployment"}

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_network_paths_permit_own_dependencies_and_deny_other_contexts(self):
        postgres = runtime._labels("postgres", "postgres")
        for service in runtime.SERVICES:
            app, proxy = runtime._labels("app", service), runtime._labels("proxy", service)
            migrator, probe = runtime._labels("migrator", service), runtime._labels("probe", service)
            port = 9000 if service in runtime.PHP_SERVICES else 8080
            with self.subTest(service=service):
                self.assertTrue(allows(self.policies, proxy, app, port))
                self.assertTrue(allows(self.policies, app, postgres, 5432))
                self.assertTrue(allows(self.policies, migrator, postgres, 5432))
                self.assertTrue(allows(self.policies, probe, proxy, 8443))
                for source, destination, denied_port in ((proxy, postgres, 5432), (probe, app, port),
                                                         (probe, postgres, 5432), (app, proxy, 8443),
                                                         (postgres, app, port), ({}, proxy, 8443)):
                    self.assertFalse(allows(self.policies, source, destination, denied_port))
                for other in set(runtime.SERVICES) - {service}:
                    self.assertFalse(allows(self.policies, runtime._labels("proxy", other), app, port))
                    self.assertFalse(allows(self.policies, runtime._labels("app", other), app, port))
                    self.assertFalse(allows(self.policies, runtime._labels("probe", other), proxy, 8443))

    def test_dns_requires_both_system_namespace_and_dns_label(self):
        policy = next(item["spec"] for item in self.policies if item["metadata"]["name"] == "cluster-dns")
        self.assertEqual(policy["egress"][0]["to"], [{
            "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "kube-system"}},
            "podSelector": {"matchLabels": {"k8s-app": "kube-dns"}}}])
        self.assertEqual(policy["egress"][0]["ports"], [{"port": 53, "protocol": "UDP"}, {"port": 53, "protocol": "TCP"}])

    def test_secret_payloads_are_private_and_not_retained_in_public_manifests(self):
        public = "\n".join((self.directory / name).read_text() for name in
                           ("resources.json", "migrations.json", "namespace.json", "kind.json", "image-imports.json", "fixture.json"))
        for secret in self.secrets:
            self.assertTrue(secret["immutable"])
            for encoded in secret["data"].values():
                self.assertNotIn(encoded, public)
                self.assertNotIn(base64.b64decode(encoded).decode().strip(), public)
        self.assertEqual(stat.S_IMODE(self.directory.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.directory / "secrets.json").stat().st_mode), 0o600)
        self.assertNotIn("ca.key", json.dumps(self.secrets))
        for service in runtime.SERVICES:
            pod = self.deployments[service]
            names = {item["secret"]["secretName"] for item in pod["volumes"] if "secret" in item}
            self.assertEqual(names, {f"{service}-runtime"})
            secret = next(item for item in self.secrets if item["metadata"]["name"] == f"{service}-runtime")
            self.assertEqual(set(secret["data"]), {"db-password", "health-token", "ca.crt"}
                             | ({"app-key"} if service in runtime.PHP_SERVICES else set()))

    def test_applications_and_jobs_cannot_receive_api_credentials_or_host_privileges(self):
        pods = list(self.deployments.items()) + [(job["metadata"]["name"], job["spec"]["template"]["spec"])
                                                 for job in self.migrations]
        for name, pod in pods:
            with self.subTest(pod=name):
                self.assertFalse(pod["automountServiceAccountToken"])
                self.assertFalse(pod["enableServiceLinks"])
                self.assertNotIn("hostNetwork", pod)
                self.assertFalse(any("hostPath" in volume for volume in pod["volumes"]))
                for container in pod["containers"] + pod.get("initContainers", []):
                    context = container["securityContext"]
                    self.assertTrue(context["readOnlyRootFilesystem"])
                    self.assertFalse(context["allowPrivilegeEscalation"])
                    self.assertEqual(context["capabilities"]["drop"], ["ALL"])
                    self.assertEqual(container["imagePullPolicy"], "Never")
                    if name != "postgres":
                        self.assertTrue(context["runAsNonRoot"])
                        self.assertEqual(context["runAsUser"], 10001)
                        self.assertNotIn("add", context["capabilities"])
        pg = self.deployments["postgres"]["containers"][0]["securityContext"]
        self.assertEqual(set(pg["capabilities"]["add"]), {"CHOWN", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID"})

    def test_public_assets_and_migrator_have_separate_authority(self):
        for service in runtime.SERVICES:
            app = self.deployments[service]["containers"][0]
            self.assertIn("exec", app["readinessProbe"])
            self.assertNotIn("readinessProbe", self.deployments[service])
            proxy = self.deployments[f"{service}-proxy"]
            if service in runtime.PHP_SERVICES:
                self.assertEqual(proxy["initContainers"][0]["image"], app["image"])
                self.assertEqual(proxy["initContainers"][0]["command"], ["/bin/sh", "-ec", "cp -R /app/public/. /srv/public/"])
            job = next(item for item in self.migrations if item["metadata"]["name"] == f"{service}-migrator")
            self.assertEqual(job["spec"]["backoffLimit"], 0)
            command = job["spec"]["template"]["spec"]["containers"][0]["command"][-1]
            self.assertIn(f"user={service}_migrator", command)
            self.assertIn("sslmode=verify-full", command)
        self.assertTrue(all(item["spec"]["type"] == "ClusterIP" for item in self.resources if item["kind"] == "Service"))

    def test_kind_requires_real_cni_and_compatible_pinned_node(self):
        kind = json.loads((self.directory / "kind.json").read_text())
        self.assertTrue(kind["networking"]["disableDefaultCNI"])
        self.assertEqual(kind["networking"]["apiServerAddress"], "127.0.0.1")
        self.assertEqual(len(kind["nodes"]), 2)
        self.assertTrue(all(runtime.NODE_IMAGE.fullmatch(node["image"]) for node in kind["nodes"]))
        self.assertTrue(json.loads((self.directory / "fixture.json").read_text())["rendered_only"])
        with self.assertRaises(ValueError):
            runtime.prepare(ROOT, self.directory.parent / "bad", IMAGES, REVISION, "kube-system")
        self.assertFalse((self.directory.parent / "bad").exists())

    def test_import_mapping_distinguishes_config_ids_from_manifest_digests(self):
        imports = json.loads((self.directory / "image-imports.json").read_text())
        for service, entry in imports["applications"].items():
            self.assertEqual(entry["local_image_id"], IMAGES[service])
            self.assertEqual(entry["kind_reference"], f"p01.local/{service}:sha256-{IMAGES[service].split(':')[1]}")
        for name, entry in imports["dependencies"].items():
            self.assertRegex(entry["source_reference"], r"^docker\.io/library/(nginx|postgres)@sha256:[0-9a-f]{64}$")
            self.assertEqual(entry["kind_reference"], f"p01.local/{name}:manifest-sha256-{entry['source_reference'].rsplit(':', 1)[1]}")
        self.assertEqual(self.deployments["postgres"]["containers"][0]["image"], imports["dependencies"]["postgres"]["kind_reference"])

    def test_leaf_certificates_verify_proxy_service_names(self):
        for service in runtime.SERVICES:
            result = subprocess.run(["openssl", "verify", "-CAfile", str(self.directory / "secrets/ca.crt"),
                                     "-verify_hostname", f"{service}-proxy", str(self.directory / "secrets" / f"{service}.crt")],
                                    capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_nginx_accepts_only_own_exact_proxy_aliases(self):
        configurations = {item["metadata"]["name"]: item["data"]["nginx.conf"]
                          for item in self.resources if item["kind"] == "ConfigMap" and "nginx.conf" in item["data"]}
        for service in runtime.SERVICES:
            configuration = configurations[f"{service}-proxy"]
            expression = re.search(r"if \(\$host !~ (.+)\) \{ return 421; \}", configuration).group(1)
            for allowed in (service, f"{service}-proxy", f"{service}-proxy.p01-test",
                            f"{service}-proxy.p01-test.svc", f"{service}-proxy.p01-test.svc.cluster.local",
                            "localhost", "127.0.0.1"):
                with self.subTest(service=service, allowed=allowed):
                    self.assertRegex(allowed, expression)
            for denied in ("attacker.example", f"{service}-proxy.p01-other", f"{service}-proxy.p01-test.svc.attacker",
                           f"prefix-{service}-proxy", f"{service}-proxy.p01-test.svc.cluster.local.attacker",
                           f"{service}-proxyXp01-testXsvcXclusterXlocal",
                           *(f"{other}-proxy.p01-test.svc.cluster.local" for other in runtime.SERVICES if other != service)):
                with self.subTest(service=service, denied=denied):
                    self.assertNotRegex(denied, expression)


if __name__ == "__main__":
    unittest.main()
