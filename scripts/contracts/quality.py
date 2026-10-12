"""Strict quality admission and semantic diff for NEW canonical releases only.

Published contract bytes are immutable. New releases must satisfy the current
profile; breaking revisions need a new MAJOR version. No legacy aliases,
migration shims, or silent waivers.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ("openapi", "schemas", "asyncapi", "capabilities", "platforms")
NAME = re.compile(r"^(.*)-v([0-9]+(?:\.[0-9]+)*)\.(json|ya?ml)$")
HTTP = {"get", "post", "put", "patch", "delete"}
MUTATIONS = {"post", "put", "patch", "delete"}


def load(path: Path):
    raw = path.read_text(encoding="utf-8")
    return yaml.safe_load(raw) if path.suffix in (".yaml", ".yml") else json.loads(raw)


def version(path: str) -> tuple[str, tuple[int, int, int]]:
    match = NAME.fullmatch(path)
    if not match:
        raise ValueError("New canonical must have a versioned filename: " + path)
    numbers = [int(x) for x in match.group(2).split(".")]
    if len(numbers) > 3:
        raise ValueError("Maximum three numeric version components: " + path)
    return match.group(1), tuple((numbers + [0, 0, 0])[:3])


def ref(schema: dict, document: dict) -> dict:
    seen = set()
    while isinstance(schema, dict) and "$ref" in schema:
        key = schema["$ref"]
        if not isinstance(key, str) or not key.startswith("#/") or key in seen:
            raise ValueError("Unsupported or circular schema reference: " + str(key))
        seen.add(key)
        current = document
        for part in key[2:].split("/"):
            current = current[part.replace("~1", "/").replace("~0", "~")]
        schema = current
    if not isinstance(schema, dict):
        raise ValueError("Expected resolved object schema")
    return schema


def type_set(schema: dict) -> set[str]:
    value = schema.get("type")
    return set(value) if isinstance(value, list) else {value} if value else set()


# Unmodelled JSON Schema assertions are never silently assumed compatible.
# Annotations can change without altering the accepted wire set.
HANDLED_ASSERTIONS = frozenset({
    "type", "const", "enum", "minimum", "maximum", "minLength",
    "maxLength", "minItems", "maxItems", "required", "items",
    "additionalProperties", "properties", "oneOf", "anyOf", "allOf",
    "not", "pattern", "patternProperties", "$ref",
})
ANNOTATIONS = frozenset({
    "$id", "$schema", "$anchor", "$comment", "title", "description",
    "examples", "deprecated",
})


def unknown_assertion_changes(old: dict, new: dict, at: str) -> list[str]:
    keys = (set(old) | set(new)) - HANDLED_ASSERTIONS - ANNOTATIONS
    return [
        at + ": unclassified schema assertion changed " + key
        for key in sorted(keys) if old.get(key) != new.get(key)
    ]


def request_breaks(old: dict, new: dict, before: dict, after: dict, at: str) -> list[str]:
    """Is every request admissible by old still admissible by new?"""
    a, b = ref(old, before), ref(new, after)
    failures = unknown_assertion_changes(a, b, at)
    if type_set(b) and (not type_set(a) or not type_set(a) <= type_set(b)):
        failures.append(at + ": request type narrowed")
    if b.get("const") is not None and a.get("const") != b["const"]:
        failures.append(at + ": request const narrowed")
    if "enum" in b and ("enum" not in a or not set(map(str, a["enum"])) <= set(map(str, b["enum"]))):
        failures.append(at + ": request enum narrowed")
    for lo, hi in (("minimum", "maximum"), ("minLength", "maxLength"),
                   ("minItems", "maxItems")):
        if lo in b and (lo not in a or b[lo] > a[lo]):
            failures.append(at + ": request minimum narrowed")
        if hi in b and (hi not in a or b[hi] < a[hi]):
            failures.append(at + ": request maximum narrowed")
    if b.get("additionalProperties") is False and a.get("additionalProperties") is not False:
        failures.append(at + ": request unknown fields newly rejected")
    ra, rb = set(a.get("required", [])), set(b.get("required", []))
    if rb - ra:
        failures.append(at + ": new required request properties " + repr(sorted(rb - ra)))
    if "items" in b and "items" not in a:
        failures.append(at + ": array item validation newly restricted")
    if "items" in a and "items" in b:
        failures.extend(request_breaks(a["items"], b["items"], before, after, at + "/items"))
    for key, value in a.get("properties", {}).items():
        if key not in b.get("properties", {}):
            if b.get("additionalProperties") is False:
                failures.append(at + ": request field removed " + key)
        else:
            failures.extend(request_breaks(value, b["properties"][key],
                                           before, after, at + "/" + key))
    # Composition/pattern changes are not provably additive; require new major.
    for key in ("oneOf", "anyOf", "allOf", "not", "pattern", "patternProperties"):
        if a.get(key) != b.get(key):
            failures.append(at + ": request constraint changed " + key)
    return failures


def response_breaks(old: dict, new: dict, before: dict, after: dict, at: str) -> list[str]:
    """Does new producer still guarantee the properties previously promised?"""
    a, b = ref(old, before), ref(new, after)
    failures = unknown_assertion_changes(a, b, at)
    if type_set(a) and (not type_set(b) or not type_set(b) <= type_set(a)):
        failures.append(at + ": response type widened")
    if a.get("const") is not None and b.get("const") != a["const"]:
        failures.append(at + ": response constant changed")
    if "enum" in a and ("enum" not in b or not set(map(str, b["enum"])) <= set(map(str, a["enum"]))):
        failures.append(at + ": response enum widened")
    if set(a.get("required", [])) - set(b.get("required", [])):
        failures.append(at + ": previously required response properties became optional")
    if a.get("additionalProperties") is False and b.get("additionalProperties") is not False:
        failures.append(at + ": response allows unknown fields")
    if a.get("additionalProperties") is False:
        added = set(b.get("properties", {})) - set(a.get("properties", {}))
        if added:
            failures.append(at + ": strict consumer sees new response fields " + repr(sorted(added)))
    for lo, hi in (("minimum", "maximum"), ("minLength", "maxLength"),
                   ("minItems", "maxItems")):
        if lo in a and (lo not in b or b[lo] < a[lo]):
            failures.append(at + ": response minimum guarantee weakened")
        if hi in a and (hi not in b or b[hi] > a[hi]):
            failures.append(at + ": response maximum guarantee weakened")
    if "items" in a and "items" not in b:
        failures.append(at + ": response array item guarantee removed")
    if "items" in a and "items" in b:
        failures.extend(response_breaks(a["items"], b["items"], before, after, at + "/items"))
    for key, item in a.get("properties", {}).items():
        if key not in b.get("properties", {}):
            failures.append(at + ": response field removed " + key)
        else:
            failures.extend(response_breaks(item, b["properties"][key], before, after,
                                            at + "/" + key))
    for key in ("oneOf", "anyOf", "allOf", "not", "pattern", "patternProperties"):
        if a.get(key) != b.get(key):
            failures.append(at + ": response constraint changed " + key)
    return failures


def body(op: dict, code: str | None = None) -> dict | None:
    if code is None:
        container = op.get("requestBody") or {}
    else:
        container = op.get("responses", {}).get(code) or {}
    media = container.get("content", {}).get("application/json")
    return media.get("schema") if isinstance(media, dict) else None


def parameters(op: dict, item: dict) -> list[dict]:
    return [*item.get("parameters", []), *op.get("parameters", [])]


def api_breakages(old: dict, new: dict) -> list[str]:
    failures = []
    if old.get("components", {}).get("securitySchemes", {}) != new.get("components", {}).get("securitySchemes", {}):
        failures.append("Underlying authentication/security-scheme definition changed")
    for path, item in old.get("paths", {}).items():
        target = new.get("paths", {}).get(path, {})
        for verb, prior in item.items():
            if verb not in HTTP:
                continue
            at = verb.upper() + " " + path
            current = target.get(verb)
            if not current:
                failures.append(at + ": operation removed")
                continue
            if prior.get("security", old.get("security", [])) != current.get("security", new.get("security", [])):
                failures.append(at + ": security/authorization requirements changed")
            if prior.get("operationId") != current.get("operationId"):
                failures.append(at + ": generated-client operationId changed")
            if prior.get("x-idempotency") != current.get("x-idempotency"):
                failures.append(at + ": idempotency scope, retention or conflict semantics changed")
            if prior.get("x-public-operation") != current.get("x-public-operation"):
                failures.append(at + ": public access contract changed")
            if prior.get("requestBody", {}).get("required") is not True and current.get("requestBody", {}).get("required") is True:
                failures.append(at + ": request body newly required")
            if set((prior.get("requestBody") or {}).get("content", {})) != set((current.get("requestBody") or {}).get("content", {})):
                failures.append(at + ": request media types changed")
            req_before, req_after = body(prior), body(current)
            if req_before is not None:
                if req_after is None:
                    failures.append(at + ": request body/schema removed")
                else:
                    failures.extend(request_breaks(req_before, req_after, old, new, at))
            old_params = {(p.get("in"), p.get("name")): p
                          for p in parameters(prior, item)}
            new_params = {(p.get("in"), p.get("name")): p
                          for p in parameters(current, target)}
            for name, parameter in old_params.items():
                replacement = new_params.get(name)
                if replacement is None:
                    failures.append(at + ": parameter removed " + repr(name))
                    continue
                if parameter.get("required") != replacement.get("required"):
                    failures.append(at + ": parameter requiredness changed " + repr(name))
                if any(parameter.get(k) != replacement.get(k)
                       for k in ("style", "explode", "allowReserved", "allowEmptyValue", "content")):
                    failures.append(at + ": parameter serialization changed " + repr(name))
                if parameter.get("schema") != replacement.get("schema"):
                    if not isinstance(parameter.get("schema"), dict) or not isinstance(replacement.get("schema"), dict):
                        failures.append(at + ": parameter schema changed " + repr(name))
                    else:
                        failures.extend(request_breaks(parameter["schema"], replacement["schema"],
                                                       old, new, at + "/parameter/" + repr(name)))
            for name, parameter in new_params.items():
                if name not in old_params and parameter.get("required"):
                    failures.append(at + ": required parameter introduced " + repr(name))
            for status, response in prior.get("responses", {}).items():
                if status not in current.get("responses", {}):
                    failures.append(at + ": response status removed " + status)
                    continue
                if set(response.get("content", {})) != set(current["responses"][status].get("content", {})):
                    failures.append(at + ": response media type changed " + status)
                if response.get("headers", {}) != current["responses"][status].get("headers", {}):
                    failures.append(at + ": response header guarantees changed " + status)
                oa, na = body(prior, status), body(current, status)
                if oa is not None and na is None:
                    failures.append(at + ": response payload removed " + status)
                elif oa is not None:
                    failures.extend(response_breaks(oa, na, old, new, at + ":" + status))
    return failures


def schema_breakages(old: dict, new: dict, at: str) -> list[str]:
    # A schema is both an inbound contract and outbound promise. Evaluate
    # both directions conservatively for same-major replacements.
    return request_breaks(old, new, old, new, at) + response_breaks(old, new, old, new, at)


def event_breakages(old: dict, new: dict) -> list[str]:
    failures = []
    for key, channel in old.get("channels", {}).items():
        successor = new.get("channels", {}).get(key)
        if not isinstance(successor, dict):
            failures.append("Event channel removed: " + key)
        elif successor.get("address") != channel.get("address"):
            failures.append("Event channel address changed: " + key)
    for key, channel in old.get("channels", {}).items():
        target = new.get("channels", {}).get(key, {})
        if target and target.get("x-delivery") != channel.get("x-delivery"):
            failures.append("Event delivery semantics changed: " + key)
        if target and target.get("messages") != channel.get("messages"):
            failures.append("Event channel message bindings changed: " + key)
    for key, message in old.get("components", {}).get("messages", {}).items():
        newer = new.get("components", {}).get("messages", {}).get(key)
        if not newer or newer.get("payload") != message.get("payload"):
            failures.append("Event payload schema binding changed: " + key)
    for key, op in old.get("operations", {}).items():
        if key not in new.get("operations", {}) or new["operations"][key].get("action") != op.get("action"):
            failures.append("Event publish/subscribe operation removed/changed: " + key)
        elif new["operations"][key].get("channel") != op.get("channel"):
            failures.append("Event operation channel binding changed: " + key)
    return failures


def quality_schema(path: str, schema: dict, policy: dict) -> None:
    if schema.get("$schema") != policy["schema_dialect"]:
        raise ValueError("New schema must use draft-2020-12: " + path)
    uid = schema.get("$id")
    parsed = urlparse(uid) if isinstance(uid, str) else None
    if not parsed or parsed.scheme != "https" or not parsed.hostname or parsed.fragment:
        raise ValueError("New canonical schema must have stable absolute HTTPS $id: " + path)
    stem, _ = version(path)
    tail = stem.split("/")[-1]
    if not (parsed.path.endswith(tail + "-v" + path.rsplit("-v", 1)[-1].split(".json")[0])
            or parsed.path.endswith(path.split("/")[-1])):
        raise ValueError("New schema $id must identify its canonical name and version: " + path)
    Draft202012Validator.check_schema(schema)
    if schema.get("type") == "object" and schema.get("additionalProperties") is not False:
        raise ValueError("New top-level object schema must reject undeclared fields: " + path)


def quality_api(path: str, doc: dict, error: dict, policy: dict) -> None:
    if doc.get("openapi") != "3.1.0":
        raise ValueError("New OpenAPI release must use 3.1.0: " + path)
    _, file_version = version(path)
    text_version = doc.get("info", {}).get("version")
    if not isinstance(text_version, str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+){0,2}", text_version):
        raise ValueError("New API must declare numeric semantic info.version: " + path)
    parsed_version = tuple((list(map(int, text_version.split("."))) + [0, 0, 0])[:3])
    if parsed_version != file_version:
        raise ValueError("OpenAPI info.version does not match versioned canonical filename: " + path)
    declared = doc.get("components", {}).get("securitySchemes", {})
    defined_error = doc.get("components", {}).get("schemas", {}).get("Error")
    stripped = {key: val for key, val in error.items() if key not in ("$id", "$schema")}
    if defined_error != stripped:
        raise ValueError("New API must embed current exact Error v2 definition: " + path)
    for endpoint, item in doc.get("paths", {}).items():
        for verb, op in item.items():
            if verb not in HTTP:
                continue
            label = path + " " + verb.upper() + " " + endpoint
            sec = op.get("security", doc.get("security"))
            if not isinstance(sec, list) or not sec or any(not isinstance(s, dict) or not s for s in sec):
                if not (endpoint in policy["public_paths"]
                        and op.get("x-public-operation") is True and sec == []):
                    raise ValueError("Security requirements missing or anonymous alternative: " + label)
            else:
                if any(not set(s).issubset(declared) for s in sec):
                    raise ValueError("Undefined security scheme: " + label)
            codes = op.get("responses", {})
            if not isinstance(codes, dict) or not any(str(c).startswith("2") for c in codes):
                raise ValueError("Operation missing successful response: " + label)
            required_errors = [] if sec == [] else policy["required_error_responses"]
            if body(op) is not None:
                required_errors = [*required_errors, policy["body_validation_status"]]
                resolved = ref(body(op), doc)
                if resolved.get("type") == "object" and resolved.get("additionalProperties") is not False:
                    raise ValueError("Request object must reject unknown fields: " + label)
            if verb in MUTATIONS:
                required_errors = [*required_errors, policy["mutation_conflict_status"]]
                headers = [param for param in parameters(op, item)
                           if param.get("in") == "header" and
                           param.get("name", "").lower() == policy["idempotency_header"].lower()]
                if len(headers) != 1 or headers[0].get("required") is not True:
                    raise ValueError("Mutation requires mandatory Idempotency-Key: " + label)
                header_schema = headers[0].get("schema", {})
                if (header_schema.get("type") != "string"
                        or type(header_schema.get("minLength")) is not int
                        or header_schema["minLength"] < 16
                        or type(header_schema.get("maxLength")) is not int
                        or header_schema["maxLength"] > 256
                        or header_schema["maxLength"] < header_schema["minLength"]):
                    raise ValueError("Mutation idempotency header must be bounded and strong: " + label)
                setting = op.get("x-idempotency", {})
                if (not isinstance(setting, dict) or
                        setting.get("scope") != policy["idempotency_scope"] or
                        not isinstance(setting.get("ttl_seconds"), int) or
                        isinstance(setting["ttl_seconds"], bool) or
                        not policy["min_idempotency_seconds"] <= setting["ttl_seconds"] <= policy["max_idempotency_seconds"] or
                        setting.get("conflict_status") != 409):
                    raise ValueError("Mutation lacks explicit scoped replay/idempotency policy: " + label)
            for status in set(required_errors):
                response = codes.get(status)
                if not isinstance(response, dict):
                    raise ValueError("Mandatory explicit error response missing " + status + ": " + label)
                schema = body(op, status)
                if schema != {"$ref": "#/components/schemas/Error"}:
                    raise ValueError("Standard Error v2 response missing " + status + ": " + label)


def quality_event(path: str, doc: dict, policy: dict, root: Path) -> None:
    if doc.get("asyncapi") != "3.0.0":
        raise ValueError("New AsyncAPI must use version 3.0.0: " + path)
    channels = doc.get("channels", {})
    messages = doc.get("components", {}).get("messages", {})
    operations = doc.get("operations", {})
    if not channels or not messages or not operations:
        raise ValueError("AsyncAPI requires channels, messages and operations: " + path)
    for key, channel in channels.items():
        delivery = channel.get("x-delivery")
        if not isinstance(delivery, dict) or delivery.get("guarantee") != policy["event_guarantee"]:
            raise ValueError("Channel missing at-least-once delivery contract: " + key)
        if (delivery.get("ordering_key") != "tenant_id"
                or delivery.get("deduplication_key") != "event_id"
                or delivery.get("acknowledgment") != "after-commit"
                or delivery.get("backoff_strategy") != "exponential-jitter"
                or type(delivery.get("dead_letter_retention_seconds")) is not int
                or not 86400 <= delivery["dead_letter_retention_seconds"] <= 7776000
                or type(delivery.get("deduplication_window_seconds")) is not int
                or not 3600 <= delivery["deduplication_window_seconds"] <= 2592000
                or not isinstance(delivery.get("dead_letter_address"), str)
                or not delivery["dead_letter_address"]
                or delivery["dead_letter_address"] == channel.get("address") or
                type(delivery.get("max_attempts")) is not int or not 1 <= delivery["max_attempts"] <= 100):
            raise ValueError("Channel missing bounded ordering, retry and DLQ rules: " + key)
        if not channel.get("address") or not channel.get("messages"):
            raise ValueError("Channel has no executable address/message binding: " + key)
    for name, msg in messages.items():
        if msg.get("contentType") != "application/json":
            raise ValueError("New message must use application/json: " + name)
        pointer = msg.get("payload", {}).get("schema", {}).get("$ref")
        if not isinstance(pointer, str) or not pointer.startswith("../schemas/events/"):
            raise ValueError("Event payload requires active canonical event schema: " + name)
        source = (root / path).parent / pointer
        source = source.resolve()
        if not source.is_relative_to((root / "contracts/schemas/events").resolve()) or not source.is_file():
            raise ValueError("Event payload references unavailable canonical schema: " + name)
        payload = load(source)
        fields = set(payload.get("required", []))
        if not set(policy["event_required_fields"]) <= fields or payload.get("additionalProperties") is not False:
            raise ValueError("Event message lacks mandatory immutable envelope: " + name)
    for key, operation in operations.items():
        if operation.get("action") not in ("send", "receive"):
            raise ValueError("Event operation lacks explicit direction: " + key)
        if operation.get("channel", {}).get("$ref") not in {
                "#/channels/" + item for item in channels}:
            raise ValueError("Event operation references unbound channel: " + key)


def git_base_paths(root: Path, revision: str) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", revision, "--", "contracts"],
            cwd=root, check=True, capture_output=True, text=True, timeout=30
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as ex:
        raise ValueError("Cannot inspect actual Git review-base inventory") from ex
    return {path for path in result.stdout.splitlines()
            if path.startswith(tuple("contracts/" + area + "/" for area in CANONICAL))
            and path.endswith((".json", ".yaml", ".yml"))}


def check_new_releases(root: Path, revision: str) -> dict:
    policy = load(root / "architecture/contract-quality-policy.json")
    error = load(root / policy["error_schema"])
    registry = load(root / "architecture/contract-consumers.json")
    current = {entry["path"] for entry in registry["active_releases"]}
    before = git_base_paths(root, revision)
    try:
        prior_registry = json.loads(subprocess.run(
            ["git", "show", revision + ":architecture/contract-consumers.json"],
            cwd=root, check=True, capture_output=True, text=True, timeout=30
        ).stdout)
    except subprocess.CalledProcessError:
        prior_registry = {"active_releases": []}
    new = sorted(current - before)
    old_versions = {}
    for filename in sorted(before):
        try:
            stem, ver = version(filename)
        except ValueError:
            continue
        previous = old_versions.get(stem)
        if previous is None or ver > previous[0]:
            old_versions[stem] = (ver, filename)
    results = []
    for path in new:
        family, ver = version(path)
        file = root / path
        if not file.is_file():
            raise ValueError("New registered canonical does not exist: " + path)
        doc = load(file)
        kind = path.split("/")[1]
        if kind == "openapi":
            quality_api(path, doc, error, policy)
        elif kind == "asyncapi":
            quality_event(path, doc, policy, root)
        elif kind == "schemas":
            quality_schema(path, doc, policy)
        elif kind in ("capabilities", "platforms"):
            if not isinstance(doc, dict):
                raise ValueError("Non-schema canonical must be an object: " + path)
        else:
            raise ValueError("Unsupported canonical publication: " + path)
        predecessor = old_versions.get(family)
        affected = sorted({
            consumer
            for snapshot in (prior_registry, registry)
            for release in snapshot["active_releases"]
            if release["path"] == path or (predecessor is not None and release["path"] == predecessor[1])
            for consumer in release.get("consumers", [])
        })
        breaking = []
        if predecessor is not None:
            older_version, old_path = predecessor
            if ver <= older_version:
                raise ValueError("Canonical version is not newer than published predecessor: " + path)
            baseline = subprocess.run(
                ["git", "show", revision + ":" + old_path],
                cwd=root, check=True, capture_output=True, text=True, timeout=30
            ).stdout
            old = yaml.safe_load(baseline) if old_path.endswith((".yaml", ".yml")) else json.loads(baseline)
            if kind == "openapi":
                breaking = api_breakages(old, doc)
            elif kind == "asyncapi":
                breaking = event_breakages(old, doc)
            elif kind == "schemas":
                breaking = schema_breakages(old, doc, path)
            if breaking and ver[0] == older_version[0]:
                raise ValueError("Breaking change requires a NEW MAJOR version: "
                                 + path + " " + "; ".join(breaking[:12]))
        results.append({
            "path": path, "version": list(ver),
            "predecessor": predecessor[1] if predecessor else None,
            "impacted_consumers": affected,
            "breaking_changes": breaking,
        })
    return {"schema_version": 1, "review_base": revision, "new_releases": results,
            "validated": len(results), "breaking_requires_major": True}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="Trusted 40-character Git review base")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.base):
        raise ValueError("Required exact Git SHA review base")
    report = check_new_releases(ROOT, args.base)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
