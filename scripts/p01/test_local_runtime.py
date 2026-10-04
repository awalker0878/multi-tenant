"""Verify P01 installer boundaries without Docker, network access or real credentials."""
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("p01_local_runtime", Path(__file__).with_name("local_runtime.py"))
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REVISION = "1" * 40
IMAGES = {name: "sha256:" + f"{index:064x}" for index, name in enumerate(MODULE.SERVICES, 1)}


def workspace(parent: Path) -> Path:
    root = parent / "workspace"
    scripts = root / "deploy/dependencies/postgres"
    scripts.mkdir(parents=True)
    for name in ("entrypoint.sh", "initialize.sh", "migrate.sql"):
        (scripts / name).write_text("fixture\n", encoding="utf-8")
    lock = {"platform": "linux/amd64", "images": {}}
    for name, digest in (("nginx", "2" * 64), ("postgres", "3" * 64)):
        lock["images"][name] = {"digest": f"sha256:{digest}", "reference": f"docker.io/library/{name}@sha256:{digest}"}
    (scripts.parent / "inputs.lock.json").write_text(json.dumps(lock), encoding="utf-8")
    return root


class RuntimeGenerationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.parent = Path(cls.temporary.name)
        cls.root = workspace(cls.parent)
        cls.runtime = cls.parent / "runtime"
        cls.compose_path = MODULE.prepare(cls.root, cls.runtime, IMAGES, REVISION)
        cls.document = json.loads(cls.compose_path.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_pins_every_image_and_disallows_pull(self):
        services = self.document["services"]
        self.assertEqual(len(services), 15)
        for name, service in services.items():
            with self.subTest(service=name):
                self.assertEqual(service["pull_policy"], "never")
                self.assertEqual(service["platform"], "linux/amd64")
                if name in IMAGES:
                    self.assertEqual(service["image"], IMAGES[name])
                else:
                    self.assertRegex(service["image"], r"^docker\.io/library/(nginx|postgres)@sha256:[a-f0-9]{64}$")

    def test_only_loopback_tls_proxies_publish_ports(self):
        for name, service in self.document["services"].items():
            with self.subTest(service=name):
                if name.endswith("-proxy"):
                    self.assertEqual(service["ports"], [{"target": 8443, "published": "0", "host_ip": "127.0.0.1", "protocol": "tcp"}])
                else:
                    self.assertNotIn("ports", service)
                self.assertNotIn("network_mode", service)
                self.assertNotIn("privileged", service)

    def test_private_database_networks_do_not_include_proxies_or_peer_apps(self):
        services, networks = self.document["services"], self.document["networks"]
        for name in MODULE.SERVICES:
            with self.subTest(service=name):
                self.assertTrue(networks[f"db_{name}"]["internal"])
                self.assertTrue(networks[f"web_{name}"]["internal"])
                members = {member for member, value in services.items() if f"db_{name}" in value["networks"]}
                self.assertEqual(members, {name, "postgres"})
                web_members = {member for member, value in services.items() if f"web_{name}" in value["networks"]}
                self.assertEqual(web_members, {name, f"{name}-proxy"})
                ingress_members = {member for member, value in services.items() if f"ingress_{name}" in value["networks"]}
                self.assertEqual(ingress_members, {f"{name}-proxy"})
                self.assertFalse(networks[f"ingress_{name}"]["internal"])
                self.assertEqual(networks[f"ingress_{name}"]["driver_opts"],
                                 {"com.docker.network.bridge.enable_ip_masquerade": "false"})
                self.assertTrue(all(networks[network]["internal"] for network in services[name]["networks"]))

    def test_unprivileged_services_have_readonly_root_and_no_capabilities(self):
        for name, service in self.document["services"].items():
            with self.subTest(service=name):
                self.assertTrue(service["read_only"])
                self.assertEqual(service["cap_drop"], ["ALL"])
                self.assertIn("no-new-privileges:true", service["security_opt"])
                self.assertEqual(service["user"], "0:0" if name == "postgres" else "10001:10001")
                if name != "postgres":
                    self.assertNotIn("cap_add", service)
        self.assertEqual(set(self.document["services"]["postgres"]["cap_add"]), {"CHOWN", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID"})

    def test_secret_values_are_not_rendered_and_mounts_have_minimal_scope(self):
        rendered = self.compose_path.read_text(encoding="utf-8")
        self.assertEqual(stat.S_IMODE(self.runtime.stat().st_mode), 0o700)
        self.assertNotIn("ca.key", self.document["secrets"])
        for name, source in self.document["secrets"].items():
            path = Path(source["file"])
            with self.subTest(secret=name):
                self.assertTrue(path.is_absolute())
                self.assertFalse(path.is_relative_to(self.root))
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o444)
                self.assertNotIn(path.read_text(encoding="utf-8").strip(), rendered)
        for name in MODULE.SERVICES:
            app = self.document["services"][name]
            sources = {item["source"] for item in app["secrets"]}
            expected = {f"{name}-runtime-password", f"{name}-health-token", "ca.crt"}
            if name in MODULE.PHP_SERVICES:
                expected.add(f"{name}-app-key")
            self.assertEqual(sources, expected)
            self.assertNotIn("DB_PASSWORD", app["environment"])
            self.assertNotIn("APP_KEY", app["environment"])
            self.assertEqual(app["environment"]["DB_SSLMODE"], "verify-full")
            proxy_sources = {item["source"] for item in self.document["services"][f"{name}-proxy"]["secrets"]}
            self.assertEqual(proxy_sources, {f"{name}.crt", f"{name}.key"})
        pg_sources = {item["source"] for item in self.document["services"]["postgres"]["secrets"]}
        self.assertEqual(pg_sources, {"postgres-password", "postgres.key", "postgres.crt", "ca.crt"}
                         | {f"{name}-{identity}-password" for name in MODULE.SERVICES for identity in ("runtime", "migrator")})

    def test_generated_certificates_validate_against_ca_and_expected_sans(self):
        for name in (*MODULE.SERVICES, "postgres"):
            cert = self.runtime / "secrets" / f"{name}.crt"
            with self.subTest(service=name):
                result = subprocess.run(["openssl", "verify", "-CAfile", str(self.runtime / "secrets/ca.crt"),
                                         "-verify_hostname", name, str(cert)], capture_output=True)
                self.assertEqual(result.returncode, 0)
                if name != "postgres":
                    for option, value in (("-verify_hostname", "localhost"), ("-verify_ip", "127.0.0.1")):
                        result = subprocess.run(["openssl", "verify", "-CAfile", str(self.runtime / "secrets/ca.crt"),
                                                 option, value, str(cert)], capture_output=True)
                        self.assertEqual(result.returncode, 0)

    def test_php_proxy_exposes_only_public_files_and_explicit_front_controller(self):
        for name in MODULE.PHP_SERVICES:
            proxy = self.document["services"][f"{name}-proxy"]
            public = next(value for value in proxy["volumes"] if value["target"] == "/srv/public")
            self.assertEqual(public["source"], str(self.runtime / "public" / name))
            self.assertTrue(public["read_only"])
            config = (self.runtime / "nginx" / f"{name}.conf").read_text(encoding="utf-8")
            self.assertIn("location = /index.php", config)
            self.assertIn("fastcgi_param SCRIPT_FILENAME /app/public/index.php;", config)
            self.assertIn(f"fastcgi_pass {name}:9000;", config)
            self.assertIn("location ~* \\.php(?:/|$) { return 404; }", config)
            self.assertIn("location ~ (^|/)\\. { return 404; }", config)
            self.assertIn(f"if ($host !~ ^({name}|localhost|127\\.0\\.0\\.1)$) {{ return 421; }}", config)
            self.assertIn("composer\\.(json|lock)", config)
            app = self.document["services"][name]
            self.assertNotIn("entrypoint", app)
            self.assertEqual(app["command"], ["sh", "-ec", "php artisan config:cache && exec php-fpm -F"])

    def test_python_entrypoints_and_proxy_targets_match_their_owner(self):
        for name in set(MODULE.SERVICES) - MODULE.PHP_SERVICES:
            self.assertEqual(self.document["services"][name]["entrypoint"], [f"/opt/venv/bin/{name}-serve"])
            config = (self.runtime / "nginx" / f"{name}.conf").read_text(encoding="utf-8")
            self.assertIn(f"proxy_pass http://{name}:8080;", config)
            self.assertNotIn("fastcgi_pass", config)

    def test_postgres_uses_v18_data_root_and_final_server_healthcheck(self):
        pg = self.document["services"]["postgres"]
        self.assertEqual(pg["volumes"][0], {"type": "volume", "source": "postgres_data", "target": "/var/lib/postgresql"})
        self.assertEqual(pg["entrypoint"], ["/bin/bash", "/opt/foundation/entrypoint.sh"])
        self.assertEqual(pg["healthcheck"]["test"], ["CMD", "pg_isready", "-h", "127.0.0.1", "-U", "postgres"])
        self.assertIn("/opt/foundation/migrate.sql", {value["target"] for value in pg["volumes"]})

    def test_refuses_to_overwrite_existing_runtime(self):
        before = self.compose_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "must not already exist"):
            MODULE.prepare(self.root, self.runtime, IMAGES, REVISION)
        self.assertEqual(self.compose_path.read_bytes(), before)


class RuntimeInputValidationTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.root = workspace(self.parent)
        self.runtime = self.parent / "runtime"

    def test_mutable_missing_and_unexpected_application_images_fail_before_writing(self):
        invalid = [{**IMAGES, "console": "example/console:latest"},
                   {**IMAGES, "planning": "docker.io/example/planning@sha256:" + "1" * 64},
                   {**IMAGES, "unexpected": "sha256:" + "2" * 64},
                   {name: value for name, value in IMAGES.items() if name != "console"}]
        for images in invalid:
            with self.subTest(images=images), self.assertRaises(ValueError):
                MODULE.prepare(self.root, self.runtime, images, REVISION)
            self.assertFalse(self.runtime.exists())

    def test_mutable_or_wrong_repository_dependency_fails_before_writing(self):
        path = self.root / "deploy/dependencies/inputs.lock.json"
        lock = json.loads(path.read_text(encoding="utf-8"))
        for reference in ("docker.io/library/nginx:latest", "docker.io/other/nginx@sha256:" + "2" * 64):
            lock["images"]["nginx"]["reference"] = reference
            path.write_text(json.dumps(lock), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "reference"):
                MODULE.prepare(self.root, self.runtime, IMAGES, REVISION)
            self.assertFalse(self.runtime.exists())

    def test_runtime_must_be_absolute_outside_workspace_and_have_private_parent(self):
        for path in (Path("relative"), self.root / "runtime"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                MODULE.prepare(self.root, path, IMAGES, REVISION)
        self.parent.chmod(0o755)
        with self.assertRaisesRegex(ValueError, "0700"):
            MODULE.prepare(self.root, self.runtime, IMAGES, REVISION)
        self.assertFalse(self.runtime.exists())

    def test_invalid_source_revision_and_symlink_runtime_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "40-character"):
            MODULE.prepare(self.root, self.runtime, IMAGES, "main")
        self.runtime.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "must not already exist"):
            MODULE.prepare(self.root, self.runtime, IMAGES, REVISION)

    def test_generation_failure_removes_only_new_runtime(self):
        with patch.object(MODULE, "_openssl", side_effect=RuntimeError("unavailable")):
            with self.assertRaisesRegex(RuntimeError, "unavailable"):
                MODULE.prepare(self.root, self.runtime, IMAGES, REVISION)
        self.assertFalse(self.runtime.exists())
        self.assertTrue(self.root.is_dir())


if __name__ == "__main__":
    unittest.main()
