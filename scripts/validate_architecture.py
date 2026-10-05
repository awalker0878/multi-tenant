#!/usr/bin/env python3
"""Check declared ownership, source placement, manifests and static import boundaries.

Python imports are checked with ast. PHP receives a conservative lexical precheck,
not type analysis: Pest architecture tests/Deptrac/PHPStan enforce its resolved
graph and Action handle() convention in product CI. PHP App namespaces are local
to each independent Laravel service; Eloquent/facades are allowed except transport
dependencies forbidden by the pragmatic DDD convention.
No check here proves authorization, behavior, data isolation or deployed topology.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys

import yaml

try:
    import tomllib
except ImportError:  # Registry-only checks also run with the documentation Python 3.10 baseline.
    tomllib = None


LAYERS = {
    "php": {
        "domain": set(), "application": {"domain"},
        "infrastructure": {"domain", "application"},
        "delivery": {"domain", "application", "infrastructure"},
    },
    "python": {
        "domain": set(), "application": {"domain"},
        "infrastructure": {"domain", "application"},
        "interfaces": {"domain", "application"},
    },
}
PHP_DELIVERY_DIRECTORIES = {
    "Broadcasting", "Console", "Events", "Exceptions", "Http", "Jobs",
    "Listeners", "Mail", "Notifications", "Policies", "Providers", "Rules", "View",
}
PHP_TRANSPORT_NAMESPACES = {
    "Illuminate\\Http", "Illuminate\\Foundation\\Http", "Illuminate\\Console",
    "Illuminate\\Support\\Facades\\Http", "Illuminate\\Support\\Facades\\Request",
    "Illuminate\\Support\\Facades\\Response", "Illuminate\\Support\\Facades\\Route",
}
SOURCE_EXTENSIONS = {".php", ".py", ".ts", ".tsx", ".js", ".jsx", ".vue"}
MANIFEST_NAMES = {"composer.json", "pyproject.toml", "package.json"}
# These are documentation tooling, not product source. Any new support root must
# be reviewed here; arbitrary nested build/dist/vendor folders do not hide code.
SUPPORT_ROOTS = {"scripts", "tests/documentation", "tests/contracts", "spikes/compatibility"}
# P00.03 is an isolated, non-product experiment. Its exact root is excluded;
# no other spike directory or deployable source gains this exemption.
PHP_STRIP = re.compile(r"/\*.*?\*/|//[^\n]*|\#[^\n]*|'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"", re.S)
PHP_NAMES = re.compile(r"(?<![\w\\])\\?[A-Za-z_]\w*(?:\\[A-Za-z_]\w*)+\\?")


@dataclass
class Result:
    errors: list[str] = field(default_factory=list)
    sources: int = 0
    python_sources: int = 0
    php_sources: int = 0
    frontend_sources: int = 0
    manifests: int = 0
    evidence_manifests: int = 0
    services: int = 0


def under(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def distribution_matches(record, name):
    expected = record.get("package_name")
    if not isinstance(expected, str):
        return False
    if record["language"] == "python":
        normalize = lambda value: re.sub(r"[-_.]+", "-", value).lower()
        return normalize(name) == normalize(expected)
    return name == expected


def cyclic(graph: dict[str, set[str]]) -> bool:
    visiting, visited = set(), set()

    def visit(node):
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(child) for child in graph.get(node, set())):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


class Validator:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.result = Result()
        self.services, self.workers, self.packages = {}, {}, {}
        self.records = []
        self.policies = {}

    def error(self, message):
        self.result.errors.append(message)

    def path(self, value, label):
        if not isinstance(value, str) or not value or "\\" in value:
            self.error(f"{label}: expected a repository-relative POSIX path")
            return self.root
        rel = PurePosixPath(value)
        if rel.is_absolute() or ".." in rel.parts or "." == value or str(rel) != value:
            self.error(f"{label}: path escapes or is not canonical: {value}")
        candidate = self.root / value
        if not under(candidate.resolve(), self.root):
            self.error(f"{label}: resolved path escapes repository: {value}")
        return candidate

    def records_for(self, data, key):
        records = data.get(key)
        if not isinstance(records, list):
            self.error(f"Registry {key} must be a list")
            return []
        if any(not isinstance(item, dict) for item in records):
            self.error(f"Registry {key} entries must be mappings")
            return []
        return records

    def load(self):
        try:
            data = yaml.safe_load((self.root / "architecture/context-map.yaml").read_text())
        except (OSError, yaml.YAMLError) as exc:
            self.error(f"Cannot load context registry: {exc}")
            return
        if not isinstance(data, dict) or data.get("schema_version") != 2:
            self.error("Unsupported context registry schema_version")
            return
        self.policies = data.get("layer_policies", {})
        if not isinstance(self.policies, dict):
            self.error("layer_policies must be a mapping")
            return
        for language in ("php", "python"):
            policy = self.policies.get(language, {})
            if not isinstance(policy, dict) or set(policy) != set(LAYERS[language]):
                self.error(f"{language}: declared layers must match its language convention")
                continue
            graph = {}
            for name, layer in policy.items():
                expected = name.title() if language == "php" else name
                if language == "php" and name == "delivery":
                    directories = layer.get("directories") if isinstance(layer, dict) else None
                    if not isinstance(directories, list) or any(not isinstance(item, str) for item in directories) or len(directories) != len(set(directories)) or set(directories) != PHP_DELIVERY_DIRECTORIES:
                        self.error("php/delivery: standard Laravel directory registration is required")
                        continue
                elif not isinstance(layer, dict) or layer.get("directory") != expected:
                    self.error(f"{language}/{name}: invalid layer directory")
                    continue
                deps = layer.get("depends_on")
                if not isinstance(deps, list) or any(not isinstance(dep, str) for dep in deps):
                    self.error(f"{language}/{name}: depends_on must be a list of layer IDs")
                    continue
                graph[name] = set(deps)
                if len(deps) != len(set(deps)) or set(deps) != LAYERS[language][name]:
                    self.error(f"{language}/{name}: prohibited layer dependency direction")
            if cyclic(graph):
                self.error(f"{language}: layer dependency cycle")
        ids, contexts, roots, symbols = set(), set(), [], []
        for kind, target in (("services", self.services), ("workers", self.workers), ("packages", self.packages)):
            for record in self.records_for(data, kind):
                ident = record.get("id")
                if not isinstance(ident, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", ident) or ident in ids:
                    self.error(f"Missing/invalid/duplicate registration ID: {ident}")
                    continue
                ids.add(ident)
                record = dict(record, kind_group=kind)
                target[ident] = record
                self.records.append(record)
                language = record.get("language")
                if language not in {"php", "python", "typescript"} or (kind != "packages" and language == "typescript"):
                    self.error(f"{ident}: invalid implementation language")
                if not isinstance(record.get("owner_role"), str) or not record["owner_role"].strip():
                    self.error(f"{ident}: missing owner_role")
                path = self.path(record.get("root"), ident)
                roots.append((ident, path))
                expected_prefix = {"services": ("services", "apps"), "workers": ("workers",), "packages": ("packages",)}[kind]
                if not isinstance(record.get("root"), str) or record["root"].split("/")[0] not in expected_prefix:
                    self.error(f"{ident}: root is outside its registered source category")
                if record.get("code_dependencies"):
                    self.error(f"{ident}: direct service code dependencies are forbidden")
                if kind == "services":
                    context = record.get("context", {})
                    if not isinstance(context, dict):
                        self.error(f"{ident}: context must be a mapping")
                        continue
                    cid = context.get("id")
                    if not isinstance(cid, str) or cid != ident or cid in contexts:
                        self.error(f"{ident}: missing, duplicate or mismatched context ID")
                    if isinstance(cid, str):
                        contexts.add(cid)
                    source = self.path(context.get("source_root"), f"{ident} context")
                    if source == path or not under(source, path):
                        self.error(f"{ident}: context source must be inside its service root")
                    if language == "php" and (context.get("source_root") != f"{record['root']}/app" or context.get("namespace") != "App\\"):
                        self.error(f"{ident}: Laravel services require local App\\ namespace rooted at app/")
                    host_roots = record.get("host_roots", [])
                    if not isinstance(host_roots, list):
                        self.error(f"{ident}: host_roots must be a list")
                        continue
                    for host in host_roots:
                        if not isinstance(host, str):
                            self.error(f"{ident}: invalid host root")
                            continue
                        hp = self.path(f"{record['root']}/{host}", f"{ident} host")
                        if not under(hp, path) or under(source, hp) or language == "php" and under(hp, source):
                            self.error(f"{ident}: host root hides context source: {host}")
                    symbol = context.get("namespace" if language == "php" else "module")
                else:
                    symbol = record.get("namespace" if language == "php" else "module")
                if not isinstance(symbol, str) or not symbol:
                    self.error(f"{ident}: missing import namespace/module")
                else:
                    # App\\ is resolved per service Composer root, never globally.
                    if not (kind == "services" and language == "php"):
                        symbols.append((ident, language, symbol))
                    elif symbol != "App\\":
                        self.error(f"{ident}: unexpected Laravel namespace")
                if kind == "packages":
                    if record.get("kind") not in {"technical", "generated"}:
                        self.error(f"{ident}: shared domain packages are forbidden")
                    if language == "php" and isinstance(symbol, str) and (symbol.rstrip("\\") == "App" or symbol.startswith("App\\")):
                        self.error(f"{ident}: shared packages cannot claim service-local App\\ namespace")
                if kind in {"services", "packages"} and not isinstance(record.get("package_name"), str):
                    self.error(f"{ident}: missing package_name")
        if not {"console", "governance", "catalogue", "inventory", "planning", "lifecycle", "assurance"} <= set(self.services):
            self.error("Registry must retain all seven initial service/context owners")
        if self.services.get("console", {}).get("composition_only") is not True:
            self.error("Console must remain a composition-only context")
        package_names = [r["package_name"] for r in self.records if isinstance(r.get("package_name"), str)]
        if len(package_names) != len(set(package_names)):
            self.error("Duplicate manifest package_name registration")
        python_names = [re.sub(r"[-_.]+", "-", r["package_name"]).lower() for r in self.records
                        if r["language"] == "python" and isinstance(r.get("package_name"), str)]
        if len(python_names) != len(set(python_names)):
            self.error("Duplicate normalized Python package_name registration")
        for index, (ident, path) in enumerate(roots):
            for other, other_path in roots[index + 1:]:
                if under(path, other_path) or under(other_path, path):
                    self.error(f"Overlapping registered roots: {ident}, {other}")
        for index, (ident, lang, symbol) in enumerate(symbols):
            sep = "\\" if lang == "php" else "."
            for other, other_lang, other_symbol in symbols[index + 1:]:
                if lang == other_lang and (symbol.rstrip(sep) == other_symbol.rstrip(sep) or symbol.startswith(other_symbol.rstrip(sep) + sep) or other_symbol.startswith(symbol.rstrip(sep) + sep)):
                    self.error(f"Overlapping import registrations: {ident}, {other}")
        for record in self.records:
            ident = record["id"]
            key = "dependencies" if record["kind_group"] == "packages" else "allowed_packages"
            deps = record.get(key)
            if not isinstance(deps, list) or any(not isinstance(dep, str) for dep in deps):
                self.error(f"{ident}: {key} must be a list of package IDs")
            elif len(deps) != len(set(deps)) or not set(deps) <= set(self.packages):
                self.error(f"{ident}: unknown/duplicate package dependency")
            if record["kind_group"] == "workers":
                owner = self.services.get(record.get("owner_service_id"))
                if not owner or owner.get("language") != record.get("language") or owner.get("owner_role") != record.get("owner_role"):
                    self.error(f"{ident}: invalid worker context ownership")
                if "context" in record:
                    self.error(f"{ident}: worker cannot register an independent context")
                if not isinstance(record.get("include_owner_source"), bool):
                    self.error(f"{ident}: owner source inclusion must be explicitly declared")
        graph = {i: set(p.get("dependencies", [])) for i, p in self.packages.items()
                 if isinstance(p.get("dependencies"), list) and all(isinstance(dep, str) for dep in p["dependencies"])}
        if cyclic(graph):
            self.error("Shared package dependency cycle")
        self.result.services = len(self.services)

    def owner(self, path):
        return next((r for r in self.records if under(path, self.root / r["root"])), None)

    def layer(self, path, record):
        if record["kind_group"] != "services":
            return "host"
        context = self.root / record["context"]["source_root"]
        if under(path, context):
            parts = path.relative_to(context).parts
            if record["language"] == "python" and parts == ("__init__.py",):
                return "domain"  # Root initializer must not smuggle composition into every import.
            for name, config in self.policies[record["language"]].items():
                if parts[0] in config.get("directories", [config.get("directory")]):
                    if record["language"] == "php" and name in {"domain", "application"} and len(parts) < 3:
                        self.error(f"{path.relative_to(self.root)}: Domain/Application source requires a capability directory")
                    return name
        for host in record["host_roots"]:
            if under(path, self.root / record["root"] / host):
                return "host"
        self.error(f"{path.relative_to(self.root)}: source is outside registered layers/host roots")
        return "unknown"

    def import_target(self, name, language, importing_record):
        for record in self.records:
            if record["language"] != language:
                continue
            if language == "php" and record["kind_group"] == "services" and record["id"] != importing_record["id"]:
                continue  # A service's App\\ namespace only exists inside its own artifact.
            where = record["context"] if record["kind_group"] == "services" else record
            prefix = where.get("namespace" if language == "php" else "module", "").rstrip("\\")
            sep = "\\" if language == "php" else "."
            if name == prefix or name.startswith(prefix + sep):
                rest = name[len(prefix):].lstrip(sep).split(sep)[0]
                layer = next((key for key, cfg in self.policies.get(language, {}).items()
                              if rest in cfg.get("directories", [cfg.get("directory")])), "host")
                return record, layer
        return None, None

    @staticmethod
    def owns_source(record, target):
        return target["id"] == record["id"] or (
            record["kind_group"] == "workers" and target["id"] == record["owner_service_id"]
            and record["include_owner_source"]
        )

    def check_import(self, name, path, record, source_layer):
        language = record["language"]
        name = name.lstrip("\\")
        target, target_layer = self.import_target(name, language, record)
        label = str(path.relative_to(self.root))
        if language == "python" and name.split(".")[0] in {"apps", "services", "workers", "packages"}:
            self.error(f"{label}: import bypasses registered namespace/module: {name}")
            return
        if language == "php":
            if source_layer in {"domain", "application"} and any(name == prefix or name.startswith(prefix + "\\") for prefix in PHP_TRANSPORT_NAMESPACES):
                self.error(f"{label}: transport dependency is forbidden in Domain/Application: {name}")
            if name == "App" or name.startswith("App\\"):
                if record["kind_group"] != "services":
                    self.error(f"{label}: cross-context code import of service-local App\\ is forbidden: {name}")
                    return
            if name.startswith(("Product\\Contexts\\", "Services\\", "Apps\\", "Workers\\")):
                self.error(f"{label}: private service import bypasses local App\\ namespace: {name}")
                return
            if name.startswith("Product\\") and not target:
                self.error(f"{label}: unregistered shared/private namespace import: {name}")
                return
        if target:
            if target["kind_group"] == "packages":
                allowed = record.get("dependencies", record.get("allowed_packages", []))
                if target["id"] != record["id"] and target["id"] not in allowed:
                    self.error(f"{label}: undeclared shared package import {name}")
                if source_layer in {"domain", "application"}:
                    self.error(f"{label}: core layer cannot import technical utilities/generated clients: {name}")
            elif target["id"] != record["id"]:
                if not self.owns_source(record, target):
                    self.error(f"{label}: cross-context code import is forbidden: {name}")
            elif source_layer != "host" and target_layer != source_layer and target_layer not in LAYERS[language].get(source_layer, set()):
                self.error(f"{label}: inverted layer dependency {source_layer} -> {target_layer}: {name}")
        elif language == "python" and source_layer in {"domain", "application"}:
            top = name.split(".")[0]
            allowed = sys.stdlib_module_names | {"__future__"}
            if top not in allowed:
                self.error(f"{label}: core layer has an external or unresolved import: {name}")

    def python(self, path, record, layer):
        self.result.python_sources += 1
        try:
            tree = ast.parse(path.read_text(), filename=str(path))
        except (OSError, SyntaxError, UnicodeError) as exc:
            self.error(f"{path.relative_to(self.root)}: invalid Python: {exc}")
            return
        if record["kind_group"] == "services":
            source = self.root / record["context"]["source_root"]
            module = record["context"]["module"]
        else:
            module = record["module"]
            source = self.root / record["root"] / "src" / module
        if under(path, source):
            rel = path.relative_to(source).with_suffix("")
            parts = (module, *rel.parts)
            package = parts[:-1]
        else:
            package = ()
        aliases = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    aliases[alias.asname or alias.name.split(".")[0]] = alias.name if alias.asname else alias.name.split(".")[0]
            elif isinstance(node, ast.ImportFrom) and not node.level:
                for alias in node.names:
                    aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"

        def resolve(expression):
            name = ast.unparse(expression)
            top, _, rest = name.partition(".")
            return aliases.get(top, top) + ("." + rest if rest else "")

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(node.value, (ast.Name, ast.Attribute)):
                        aliases[target.id] = resolve(node.value)
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    if not package or node.level > len(package):
                        self.error(f"{path.relative_to(self.root)}: relative import escapes registered module")
                        continue
                    base = ".".join((*package[:len(package) - node.level + 1], *([base] if base else [])))
                names = [base + "." + alias.name for alias in node.names]
            for name in names:
                self.check_import(name, path, record, layer)
            # Dynamic imports and search-path mutation require a dedicated reviewed mechanism.
            if isinstance(node, ast.Call):
                func = resolve(node.func)
                if func in {"__import__", "builtins.__import__", "importlib.import_module", "importlib.util.spec_from_file_location", "exec", "builtins.exec", "eval", "builtins.eval"} or func.startswith("sys.path."):
                    self.error(f"{path.relative_to(self.root)}: dynamic loading/search-path mutation needs an explicit reviewed mechanism: {func}")

    def php(self, path, record, layer):
        self.result.php_sources += 1
        code = PHP_STRIP.sub(" ", path.read_text())
        names = {m.group().strip("\\") for m in PHP_NAMES.finditer(code)}
        names.update(re.findall(r"\buse\s+(?:function\s+|const\s+)?([A-Za-z_]\w*)\s*(?:as\s+\w+)?;", code))
        for name in names:
            self.check_import(name, path, record, layer)
        if record["kind_group"] == "services" and layer not in {"host", "unknown"}:
            declaration = re.search(r"\bnamespace\s+([\w\\]+)\s*[;{]", code)
            parent = path.parent.relative_to(self.root / record["context"]["source_root"])
            expected = record["context"]["namespace"] + "\\".join(parent.parts)
            if not declaration or declaration[1] != expected:
                self.error(f"{path.relative_to(self.root)}: namespace does not match owning context/layer")

    def local_reference(self, value, manifest, record):
        # Dependency paths are relative to the package manifest; ../ is allowed only
        # to an explicitly declared shared package, never a sibling service.
        value = value.removeprefix("file:")
        if not value or Path(value).is_absolute() or any(ch in value for ch in ("*", "?", "\\")):
            self.error(f"{manifest.relative_to(self.root)}: unsupported/absolute local dependency: {value}")
            return
        target = (manifest.parent / value).resolve()
        if not under(target, self.root):
            self.error(f"{manifest.relative_to(self.root)}: dependency path escapes repository: {value}")
            return
        owner = self.owner(target)
        allowed = record.get("dependencies", record.get("allowed_packages", []))
        if not owner or owner["id"] != record["id"] and (owner["kind_group"] != "packages" or owner["id"] not in allowed):
            self.error(f"{manifest.relative_to(self.root)}: unregistered/cross-service local dependency: {value}")

    def source_mapping(self, value, manifest):
        if not isinstance(value, str) or Path(value).is_absolute() or not under((manifest.parent / value).resolve(), manifest.parent):
            self.error(f"{manifest.relative_to(self.root)}: build/autoload source mapping escapes service/package: {value}")

    def manifest(self, path, record):
        self.result.manifests += 1
        if path.parent != self.root / record["root"]:
            self.error(f"{path.relative_to(self.root)}: nested package manifests require separate registration")
            return
        try:
            if path.suffix == ".toml":
                if tomllib is None:
                    self.error("Python 3.11+ is required to validate pyproject.toml files")
                    return
                data = tomllib.loads(path.read_text())
            else:
                data = json.loads(path.read_text())
            if not isinstance(data, dict):
                raise ValueError("manifest must contain an object")
        except (OSError, ValueError) as exc:
            self.error(f"{path.relative_to(self.root)}: invalid manifest: {exc}")
            return
        def walk(value, key=""):
            if isinstance(value, dict):
                if value.get("type") == "path" and isinstance(value.get("url"), str):
                    self.local_reference(value["url"], path, record)
                for name, child in value.items():
                    foreign = next((s for s in self.services.values() if distribution_matches(s, name)), None)
                    if foreign and not self.owns_source(record, foreign):
                        self.error(f"{path.relative_to(self.root)}: direct service package dependency is forbidden: {name}")
                    package = next((p for p in self.packages.values() if distribution_matches(p, name)), None)
                    if package and package["id"] != record["id"] and package["id"] not in record.get("allowed_packages", record.get("dependencies", [])):
                        self.error(f"{path.relative_to(self.root)}: undeclared shared package dependency: {name}")
                    if name in {"package-dir", "package_dir"} and isinstance(child, dict):
                        for directory in child.values():
                            self.source_mapping(directory, path)
                    if name in {"module-root", "from"} and isinstance(child, str):
                        self.source_mapping(child, path)
                    if name == "backend-path" and isinstance(child, list):
                        for directory in child:
                            self.source_mapping(directory, path)
                    if name == "path" and isinstance(child, str):
                        self.local_reference(child, path, record)
                    else:
                        walk(child, name)
            elif isinstance(value, list):
                for child in value:
                    walk(child, key)
            elif isinstance(value, str):
                declared_name = re.split(r"[\s\[<>=!~;]", value, maxsplit=1)[0]
                foreign = next((s for s in self.services.values() if distribution_matches(s, declared_name)), None)
                if foreign and not self.owns_source(record, foreign) and key != "name":
                    self.error(f"{path.relative_to(self.root)}: direct service package dependency is forbidden: {declared_name}")
                package = next((p for p in self.packages.values() if distribution_matches(p, declared_name)), None)
                if package and package["id"] != record["id"] and key != "name" and package["id"] not in record.get("allowed_packages", record.get("dependencies", [])):
                    self.error(f"{path.relative_to(self.root)}: undeclared shared package dependency: {declared_name}")
                match = re.search(r"(?:^|\s@\s)(file:.*)$", value)
                if match:
                    self.local_reference(match[1], path, record)
                if value.startswith(("link:", "portal:")):
                    self.local_reference(value.split(":", 1)[1], path, record)
                if value.startswith("workspace:"):
                    package = next((p for p in self.packages.values() if p["package_name"] == key), None)
                    if not package or package["id"] not in record.get("allowed_packages", record.get("dependencies", [])):
                        self.error(f"{path.relative_to(self.root)}: undeclared workspace dependency: {key}")
        walk(data)
        if path.name == "composer.json":
            for section in ("autoload", "autoload-dev"):
                for strategy in ("psr-4", "psr-0", "classmap", "files"):
                    entries = data.get(section, {}).get(strategy, {})
                    values = entries.values() if isinstance(entries, dict) else entries
                    for value in values:
                        for item in value if isinstance(value, list) else [value]:
                            target = (path.parent / item).resolve()
                            if not under(target, path.parent):
                                self.error(f"{path.relative_to(self.root)}: autoload source escapes service/package: {item}")
            if record["kind_group"] == "services":
                mapping = data.get("autoload", {}).get("psr-4", {})
                expected = record["context"]["namespace"]
                target = mapping.get(expected)
                correct = str((self.root / record["context"]["source_root"]).relative_to(path.parent))
                if not isinstance(target, str) or target.rstrip("/") != correct:
                    self.error(f"{path.relative_to(self.root)}: missing/exact context PSR-4 mapping required: {expected} -> {correct}/")

    def retained_manifest(self, path):
        """Classify a bound P01 manifest snapshot without excluding evidence source."""
        parts = path.relative_to(self.root).parts
        if (path.name not in MANIFEST_NAMES or len(parts) != 6
                or parts[:3] != ("verification", "p01", "packages")
                or not re.fullmatch(r"run-[1-9][0-9]*", parts[3])):
            return False
        record = self.services.get(parts[4]) or self.workers.get(parts[4])
        if not record:
            return False
        permitted = {"pyproject.toml"} if record["language"] == "python" else {"composer.json"}
        if record["id"] == "console":
            permitted.add("package.json")
        if path.name not in permitted:
            return False
        label = str(path.relative_to(self.root))
        report_path = path.with_name("report.json")
        try:
            if report_path.is_symlink() or not report_path.is_file():
                raise ValueError("a regular sibling report.json is required")
            report = json.loads(report_path.read_text())
            if (not isinstance(report, dict) or report.get("schema_version") != 1
                    or report.get("component") != record["id"]
                    or report.get("run_id") != parts[3].removeprefix("run-")
                    or not isinstance(report.get("source_sha"), str)
                    or not re.fullmatch(r"[0-9a-f]{40}", report["source_sha"])):
                raise ValueError("report identity does not match its evidence location")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            for key, name in (("artifact_sha256", path.name),
                              ("source_sha256", f"{record['root']}/{path.name}")):
                bindings = report.get(key)
                if not isinstance(bindings, dict) or bindings.get(name) != digest:
                    raise ValueError(f"{key} does not bind the retained manifest bytes")
        except (OSError, ValueError) as exc:
            self.error(f"{label}: invalid retained evidence manifest: {exc}")
        else:
            self.result.evidence_manifests += 1
        return True

    def run(self):
        self.load()
        if self.result.errors:
            return self.result
        excluded = {self.root / name for name in {".git", ".venv"} | SUPPORT_ROOTS}
        excluded.update(self.root / record["root"] / name for record in self.records for name in ("vendor", "node_modules", ".venv"))
        for directory, dirs, files in os.walk(self.root, followlinks=False):
            parent = Path(directory)
            for name in list(dirs):
                path = parent / name
                if path.is_symlink():
                    self.error(f"{path.relative_to(self.root)}: source/dependency symlinks are forbidden")
                    dirs.remove(name)
                elif path in excluded:
                    dirs.remove(name)
            for name in sorted(files):
                path = parent / name
                if path.suffix not in SOURCE_EXTENSIONS and path.name not in MANIFEST_NAMES:
                    continue
                if path.is_symlink():
                    self.error(f"{path.relative_to(self.root)}: source/dependency symlinks are forbidden")
                    continue
                if self.retained_manifest(path):
                    continue
                record = self.owner(path)
                if not record:
                    self.error(f"{path.relative_to(self.root)}: unregistered source or manifest root")
                    continue
                if path.name in MANIFEST_NAMES:
                    self.manifest(path, record)
                    continue
                self.result.sources += 1
                layer = self.layer(path, record)
                expected = "php" if path.suffix == ".php" else "python" if path.suffix == ".py" else "typescript"
                if expected != record["language"] and not (record["id"] == "console" and expected == "typescript" and layer == "host"):
                    self.error(f"{path.relative_to(self.root)}: source language differs from registered owner")
                    continue
                if expected == "python":
                    self.python(path, record, layer)
                elif expected == "php":
                    self.php(path, record, layer)
                else:
                    self.result.frontend_sources += 1
        return self.result


def validate(root: Path) -> Result:
    return Validator(root).run()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = validate(args.root)
    if result.errors:
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Architecture registry passed: {result.services} services; {result.manifests} manifests checked.")
    if result.evidence_manifests:
        print(f"Retained evidence: {result.evidence_manifests} manifest snapshots classified separately; source and artifact hashes matched their reports.")
    if not result.sources:
        print("Application source absent: source-boundary checks have not yet been exercised on product code.")
    else:
        print(f"Source placement passed: {result.sources} files; Python AST imports: {result.python_sources}; PHP conservative precheck: {result.php_sources}; frontend placement only: {result.frontend_sources}.")
        print("Resolved PHP/TypeScript graphs, dynamic imports, runtime wiring and behavior require their implementation CI gates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
