#!/usr/bin/env python3
"""Bounded PostgreSQL and attachment rebuild/restore candidate experiment."""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import uuid

DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def validate_lock(lock: dict, candidate: dict, candidate_sha: str) -> None:
    repository = candidate["image"].rsplit(":", 1)[0]
    if lock.get("schema_version") != 1 or lock.get("candidate_sha256") != candidate_sha:
        raise ValueError("LOCK_CANDIDATE_MISMATCH")
    if lock.get("platform") != candidate["platform"] or lock.get("candidate") != candidate["image"]:
        raise ValueError("LOCK_SELECTION_MISMATCH")
    if not DIGEST.fullmatch(lock.get("index_digest", "")) or not DIGEST.fullmatch(lock.get("digest", "")):
        raise ValueError("LOCK_DIGEST_REQUIRED")
    if lock.get("reference") != repository + "@" + lock["digest"]:
        raise ValueError("LOCK_IMMUTABLE_REPOSITORY_REQUIRED")


def validate_bundle(bundle: Path, manifest_digest: str) -> dict:
    """Fail before creating any restore database; digest is held outside the bundle."""
    if sha(bundle / "manifest.json") != manifest_digest:
        raise ValueError("BUNDLE_MANIFEST_DIGEST_MISMATCH")
    manifest = json.loads((bundle / "manifest.json").read_bytes())
    expected = set(manifest["artifacts"]) | {"manifest.json"}
    observed = {str(p.relative_to(bundle)) for p in bundle.rglob("*") if p.is_file()}
    if expected != observed:
        raise ValueError("BUNDLE_ARTIFACT_SET_MISMATCH")
    for name, record in manifest["artifacts"].items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("BUNDLE_UNSAFE_PATH")
        path = bundle / relative
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != bundle.parent):
            raise ValueError("BUNDLE_SYMLINK_REJECTED")
        if sha(path) != record["sha256"] or path.stat().st_size != record["bytes"]:
            raise ValueError("BUNDLE_ARTIFACT_DIGEST_MISMATCH:" + name)
    required = {"database.dump", "snapshot.json", "configuration.json", "writers.json"}
    if not required <= set(manifest["artifacts"]):
        raise ValueError("BUNDLE_REQUIRED_STATE_MISSING")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("resolve", "replay"), default="replay")
    parser.add_argument("--lock", type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    source = workspace / "spikes/compatibility/restore"
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    evidence = output / "evidence"
    evidence.mkdir()
    work = output / "work"
    work.mkdir()
    candidate_path = source / "candidate.json"
    candidate = json.loads(candidate_path.read_bytes())
    state = {
        "schema_version": 1, "result": "RUNNING", "started_at": now(), "mode": args.mode,
        "scope": "Synthetic PostgreSQL and attachment fixture on one disposable Docker host; no VMware/OpenStack, native fence, business application, operating acceptance or G00 pass",
        "source_sha": os.getenv("GITHUB_SHA"), "source_ref": os.getenv("GITHUB_REF"),
        "run_id": os.getenv("GITHUB_RUN_ID"), "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
        "candidate": candidate, "source_sha256": {}, "commands": [], "checks": [], "boundaries": [],
    }
    for path in sorted(source.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            state["source_sha256"][str(path.relative_to(workspace))] = sha(path)
    for path in sorted((workspace / ".github/workflows").glob("*.yml")):
        state["source_sha256"][str(path.relative_to(workspace))] = sha(path)
    token = uuid.uuid4().hex[:12]
    container_name = "p00-restore-" + token
    container_started = False
    gates: dict[str, bool] = {}
    dump_sequence = 0

    def save() -> None:
        write_json(evidence / "report.json", state)

    def command(label: str, argv: list[str], *, stdin: str | None = None, input_file: Path | None = None,
                timeout: int = 120, expected: str | None = None, cleanup: bool = False) -> str:
        index = len(state["commands"]) + 1
        entry = {"label": label, "command": argv, "log": f"{index:03d}-{label}.log", "started_at": now()}
        if stdin is not None:
            entry["stdin"] = stdin  # Only synthetic SQL; no credentials or native endpoint inputs.
        if input_file is not None:
            entry["stdin_file_sha256"] = sha(input_file)
            entry["stdin_file_bytes"] = input_file.stat().st_size
        state["commands"].append(entry)
        save()
        started = time.monotonic()
        with (evidence / entry["log"]).open("wb") as log:
            try:
                proc = subprocess.Popen(argv, stdin=subprocess.PIPE if stdin is not None or input_file is not None else subprocess.DEVNULL,
                                        stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    data = input_file.read_bytes() if input_file is not None else None if stdin is None else stdin.encode()
                    proc.communicate(data, timeout=timeout)
                    entry["exit_code"] = proc.returncode
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=5)
                    entry["exit_code"] = 124
                    log.write(b"\nBounded command timeout exceeded.\n")
            except OSError as error:
                entry["exit_code"] = 127
                log.write((str(error) + "\n").encode())
        entry["duration_seconds"] = round(time.monotonic() - started, 3)
        entry["log_sha256"] = sha(evidence / entry["log"])
        result = (evidence / entry["log"]).read_bytes().decode("utf-8", errors="replace")
        if expected is not None:
            entry["expected_diagnostic"] = expected
            passed = entry["exit_code"] not in (0, 124, 127) and expected in result
            entry["result"] = "EXPECTED_REJECTION" if passed else "FAILED"
        else:
            passed = entry["exit_code"] == 0
            entry["result"] = "PASS" if passed else "FAILED"
        save()
        print(f"{label}: {entry['result']} (exit {entry['exit_code']})", flush=True)
        if not passed and not cleanup:
            print(result[-12000:], flush=True)
            raise RuntimeError(f"{label} failed its exact exit/diagnostic expectation")
        return result

    def sql(label: str, database: str, query: str, *, role: str = "postgres", expected: str | None = None) -> str:
        return command(label, ["docker", "exec", "-i", container_name, "psql", "-X", "-qAt",
                               "--set", "ON_ERROR_STOP=1", "--username", role, "--dbname", database],
                       stdin=query + "\n", expected=expected).strip()

    def check(name: str, actual: object, expected: object = True) -> None:
        passed = actual == expected
        state["checks"].append({"name": name, "result": "PASS" if passed else "FAILED", "actual": actual, "expected": expected})
        save()
        if not passed:
            raise RuntimeError("Check failed: " + name)

    def snapshot(database: str, label: str) -> dict:
        return json.loads(sql(label, database, (source / "snapshot.sql").read_text()))

    def exists(database: str, label: str) -> bool:
        return sql(label, "postgres", f"SELECT count(*) FROM pg_database WHERE datname = '{database}';") == "1"

    def gate(database: str, enabled: bool) -> None:
        role = database + "_writer"
        sql("enable-" + database if enabled else "quiesce-" + database, "postgres",
            f"ALTER ROLE {role} {'LOGIN' if enabled else 'NOLOGIN'};\n"
            + ("" if enabled else f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = '{role}' AND pid <> pg_backend_pid();"))
        gates[database] = enabled
        state["boundaries"].append({"at": now(), "database": database, "fixture_writer_enabled": enabled,
                                    "meaning": "Fixture PostgreSQL role gate only; admin bypass remains, no native fencing claim"})
        save()

    def verify_data(database: str, files: Path, expected: dict, label: str) -> dict:
        current = snapshot(database, label + "-snapshot")
        check(label + "-records", current, expected)
        actual_paths = {str(p.relative_to(files)) for p in files.rglob("*") if p.is_file()}
        check(label + "-attachment-set", sorted(actual_paths), sorted(a["path"] for a in current["attachments"]))
        for attachment in current["attachments"]:
            path = files / attachment["path"]
            check(label + "-" + attachment["attachment_id"] + "-digest", sha(path), attachment["sha256"])
            check(label + "-" + attachment["attachment_id"] + "-bytes", path.stat().st_size, attachment["bytes"])
            check(label + "-" + attachment["attachment_id"] + "-mode", f"{path.stat().st_mode & 0o777:04o}", attachment["file_mode"])
        orphan_count = sql(label + "-relationships", database,
                           "SELECT count(*) FROM attachments a LEFT JOIN permits p ON (a.tenant_id, a.permit_id) = (p.tenant_id, p.permit_id) WHERE p.permit_id IS NULL;")
        check(label + "-no-orphans", orphan_count, "0")
        return current

    def capture(database: str, files: Path, name: str) -> tuple[Path, str, dict]:
        nonlocal dump_sequence
        if gates.get(database) is not False:
            raise RuntimeError("CAPTURE_REQUIRES_QUIESCED_FIXTURE_WRITER")
        # The only attachment writer is this synchronous runner. No writes occur between
        # the snapshot, PostgreSQL export and file copy; the role gate prevents DB writers.
        bundle = work / name
        bundle.mkdir()
        captured = snapshot(database, name + "-snapshot")
        write_json(bundle / "snapshot.json", captured)
        dump_sequence += 1
        remote_dump = f"/tmp/capture-{dump_sequence}.dump"
        command(name + "-pg-dump", ["docker", "exec", container_name, "pg_dump", "--username", "postgres",
                                   "--dbname", database, "--format=custom", "--no-owner", "--no-acl", "--file", remote_dump])
        command(name + "-copy-dump", ["docker", "cp", container_name + ":" + remote_dump, str(bundle / "database.dump")])
        shutil.copytree(files, bundle / "attachments")
        write_json(bundle / "configuration.json", {
            "fixture": "Permit Desk synthetic state only", "image_reference": state["image"]["reference"],
            "server_version_num": state["server_version_num"], "encoding": "UTF8", "locale": "C",
            "schema_sha256": sha(source / "schema.sql"), "attachment_mode": "0640",
            "secret_references": [], "identity": "Disposable local fixture roles; production identity absent",
            "external_dependencies": [], "mail_jobs_and_network_effects": "ABSENT from this fixture",
            "state_inventory": ["tenants", "permits", "attachments metadata", "write_markers", "attachment bytes"],
            "excluded_unimplemented_application_state": ["web service", "sessions", "external identity", "keys", "shared services", "guest OS customizations"],
        })
        write_json(bundle / "writers.json", {
            "database_writer": database + "_writer", "database_login_enabled": False,
            "attachment_writer": "Single synchronous run.py process; no other fixture file writer",
            "setup_capture_restore_administrator": "postgres via local Docker exec; not subject to fixture gate",
            "background_writers": [], "external_writers": [], "native_fencing": "NOT_IMPLEMENTED",
            "consistency_boundary": "Disable fixture database login, terminate its sessions, stop runner attachment writes, snapshot/export/copy before re-enabling any writer",
        })
        artifacts = {str(p.relative_to(bundle)): {"sha256": sha(p), "bytes": p.stat().st_size}
                     for p in sorted(bundle.rglob("*")) if p.is_file()}
        manifest = {"schema_version": 1, "captured_at": now(), "database": database,
                    "source_sha": state["source_sha"], "source_snapshot_sha256": sha(bundle / "snapshot.json"),
                    "artifacts": artifacts}
        write_json(bundle / "manifest.json", manifest)
        digest = sha(bundle / "manifest.json")
        validate_bundle(bundle, digest)
        verify_data(database, files, captured, name + "-stable-source")
        # Text envelope preserves every captured byte for durable source-controlled evidence.
        # PostgreSQL custom archives include run metadata and are not expected byte-identical.
        envelope = {"manifest_sha256": digest, "files_base64": {
            str(p.relative_to(bundle)): base64.b64encode(p.read_bytes()).decode()
            for p in sorted(bundle.rglob("*")) if p.is_file()}}
        write_json(evidence / (name + "-bundle.json"), envelope)
        state.setdefault("captures", []).append({"name": name, "database": database, "manifest_sha256": digest,
                                                  "archive_sha256": artifacts["database.dump"]["sha256"],
                                                  "bytes": sum(x["bytes"] for x in artifacts.values()),
                                                  "evidence_envelope": name + "-bundle.json"})
        save()
        return bundle, digest, captured

    def restore(bundle: Path, digest: str, database: str, label: str) -> Path:
        validate_bundle(bundle, digest)  # MUST precede CREATE DATABASE, copying or pg_restore.
        if exists(database, label + "-check-absent"):
            raise RuntimeError("RESTORE_REQUIRES_CLEAN_DATABASE")
        sql(label + "-create", "postgres", f"CREATE DATABASE {database} TEMPLATE template0 ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C';")
        command(label + "-pg-restore", ["docker", "exec", "-i", container_name, "pg_restore", "--username", "postgres",
                                        "--dbname", database, "--exit-on-error", "--single-transaction",
                                        "--no-owner", "--no-acl"], input_file=bundle / "database.dump")
        files = work / (database + "-attachments")
        shutil.copytree(bundle / "attachments", files)
        sql(label + "-writer-grants", database,
            f"GRANT USAGE ON SCHEMA public TO {database}_writer; GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {database}_writer;")
        gates[database] = False
        expected = json.loads((bundle / "snapshot.json").read_bytes())
        verify_data(database, files, expected, label + "-verify")
        return files

    try:
        command("docker-version", ["docker", "version"], timeout=30)
        command("buildx-version", ["docker", "buildx", "version"], timeout=30)
        if args.mode == "resolve":
            detail = command("resolve-postgres", ["docker", "buildx", "imagetools", "inspect", candidate["image"]])
            matched = re.search(r"^Digest:\s+(sha256:[0-9a-f]{64})\s*$", detail, re.MULTILINE)
            if matched is None:
                raise RuntimeError("Image registry did not return an index digest")
            index_digest = matched.group(1)
            repository = candidate["image"].rsplit(":", 1)[0]
            raw = command("postgres-manifest", ["docker", "buildx", "imagetools", "inspect", "--raw", repository + "@" + index_digest])
            index = json.loads(raw)
            matches = [m["digest"] for m in index.get("manifests", [])
                       if m.get("platform", {}).get("os") == "linux" and m.get("platform", {}).get("architecture") == "amd64"]
            if len(matches) != 1:
                raise RuntimeError("Expected exactly one linux/amd64 child manifest")
            lock = {"schema_version": 1, "candidate": candidate["image"], "candidate_sha256": sha(candidate_path),
                    "platform": candidate["platform"], "resolved_at": now(), "index_digest": index_digest,
                    "digest": matches[0], "reference": repository + "@" + matches[0]}
        else:
            lock = json.loads((args.lock or source / "inputs.lock.json").read_bytes())
        validate_lock(lock, candidate, sha(candidate_path))
        write_json(evidence / "inputs.lock.json", lock)
        state["lock_sha256"] = sha(evidence / "inputs.lock.json")
        for label, mutate, diagnostic in [
            ("mutable-reference", lambda x: x.update(reference=candidate["image"]), "LOCK_IMMUTABLE_REPOSITORY_REQUIRED"),
            ("changed-input", lambda x: x.update(candidate_sha256="0" * 64), "LOCK_CANDIDATE_MISMATCH"),
            ("changed-platform", lambda x: x.update(platform="linux/arm64"), "LOCK_SELECTION_MISMATCH"),
        ]:
            changed = dict(lock)
            mutate(changed)
            try:
                validate_lock(changed, candidate, sha(candidate_path))
            except ValueError as error:
                check("lock-reject-" + label, str(error), diagnostic)
            else:
                raise RuntimeError("Invalid lock accepted: " + label)
        reference = lock["reference"]
        command("pull-postgres", ["docker", "pull", "--platform", candidate["platform"], reference], timeout=300)
        image = json.loads(command("image-inspect", ["docker", "image", "inspect", reference]))[0]
        check("image-platform", [image["Os"], image["Architecture"]], ["linux", "amd64"])
        state["image"] = {"reference": reference, "config_digest": image["Id"], "layers": image["RootFS"]["Layers"], "repo_digests": image["RepoDigests"]}
        uid = command("postgres-uid", ["docker", "run", "--rm", "--network", "none", "--entrypoint", "id", reference, "-u", "postgres"]).strip()
        gid = command("postgres-gid", ["docker", "run", "--rm", "--network", "none", "--entrypoint", "id", reference, "-g", "postgres"]).strip()
        check("nonroot-postgres-uid", uid.isdigit() and uid != "0")
        container_started = True  # Cleanup even if Docker returns after creation but before acknowledgement.
        command("start-postgres", ["docker", "run", "-d", "--name", container_name, "--network", "none",
                "--user", uid + ":" + gid, "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
                "--pids-limit", "128", "--memory", "768m", "--cpus", "1", "--read-only",
                "--tmpfs", f"/var/lib/postgresql:rw,nosuid,nodev,size=256m,uid={uid},gid={gid}",
                "--tmpfs", f"/var/run/postgresql:rw,nosuid,nodev,size=16m,uid={uid},gid={gid}",
                "--tmpfs", f"/tmp:rw,nosuid,nodev,size=64m,uid={uid},gid={gid}",
                "-e", "POSTGRES_HOST_AUTH_METHOD=trust", "-e", "POSTGRES_INITDB_ARGS=--encoding=UTF8 --locale=C",
                reference, "postgres", "-c", "listen_addresses=", "-c", "max_connections=20"], timeout=120)
        command("wait-postgres", ["docker", "exec", container_name, "sh", "-c",
                "i=0; until [ \"$(cat /proc/1/comm)\" = postgres ] && pg_isready -U postgres -d postgres >/dev/null 2>&1; do i=$((i+1)); [ \"$i\" -lt 60 ] || exit 1; sleep 1; done"], timeout=70)
        state["server_version_num"] = sql("server-version-num", "postgres", "SHOW server_version_num;")
        check("exact-postgres-version", state["server_version_num"], candidate["expected_server_version_num"])
        command("server-runtime", ["docker", "exec", container_name, "sh", "-c", "id; postgres --version; psql --version; pg_dump --version; pg_restore --version; cat /etc/os-release"])
        command("os-packages", ["docker", "exec", container_name, "dpkg-query", "-W", "-f=${Package}\t${Version}\t${Architecture}\n"])
        state["container"] = json.loads(command("container-inspect", ["docker", "inspect", container_name]))[0]
        check("network-none", state["container"]["HostConfig"]["NetworkMode"], "none")
        check("no-published-ports", state["container"]["HostConfig"].get("PortBindings") in ({}, None))
        check("postgres-no-tcp-listener", sql("listen-addresses", "postgres", "SHOW listen_addresses;"), "")
        sql("create-fixture-roles", "postgres", "\n".join(f"CREATE ROLE {d}_writer NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;" for d in ["source", "target", "recovery"]))
        sql("create-source", "postgres", "CREATE DATABASE source TEMPLATE template0 ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C';")
        sql("schema-source", "source", (source / "schema.sql").read_text())
        files = work / "source-attachments"
        files.mkdir()
        statements = ["INSERT INTO tenants VALUES ('tenant_a', 'Synthetic A'), ('tenant_b', 'Synthetic B');"]
        for tenant in ["tenant_a", "tenant_b"]:
            for number in (1, 2):
                pid = f"{tenant}_permit_{number}"
                aid = f"{tenant}_attachment_{number}"
                relative = f"{tenant}/{pid}.txt"
                path = files / relative
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(f"Permit Desk synthetic attachment\nTenant={tenant}\nPermit={pid}\nSeed=p00-v1\n".encode())
                path.chmod(0o640)
                statements += [f"INSERT INTO permits VALUES ('{tenant}', '{pid}', 'Synthetic permit {number}', 'submitted');",
                               f"INSERT INTO attachments VALUES ('{tenant}', '{aid}', '{pid}', '{relative}', '{sha(path)}', {path.stat().st_size}, '0640');"]
        statements += ["INSERT INTO write_markers VALUES ('last_source_write', 'tenant_a', 'Synthetic source capture boundary');",
                       "GRANT USAGE ON SCHEMA public TO source_writer; GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO source_writer;"]
        sql("seed-source", "source", "\n".join(statements))
        gate("source", True)
        sql("source-writer-read", "source", "SELECT count(*) FROM permits;", role="source_writer")
        gate("source", False)
        sql("source-write-denied", "source", "INSERT INTO write_markers VALUES ('forbidden', 'tenant_a', 'must not commit');",
            role="source_writer", expected='role "source_writer" is not permitted to log in')
        bundle, digest, baseline = capture("source", files, "initial-capture")

        for label, mutate, diagnostic in [
            ("corrupted-dump", lambda b: (b / "database.dump").write_bytes(b"corrupt"), "BUNDLE_ARTIFACT_DIGEST_MISMATCH:database.dump"),
            ("missing-attachment", lambda b: next((b / "attachments").rglob("*.txt")).unlink(), "BUNDLE_ARTIFACT_SET_MISMATCH"),
            ("unexpected-file", lambda b: (b / "untracked-state.txt").write_text("unexpected"), "BUNDLE_ARTIFACT_SET_MISMATCH"),
            ("modified-manifest", lambda b: (b / "manifest.json").write_text("{}"), "BUNDLE_MANIFEST_DIGEST_MISMATCH"),
        ]:
            bad = work / label
            shutil.copytree(bundle, bad)
            mutate(bad)
            try:
                restore(bad, digest, "rejected", label)
            except ValueError as error:
                check(label + "-exact-rejection", str(error), diagnostic)
                check(label + "-before-database-create", exists("rejected", label + "-no-target"), False)
            else:
                raise RuntimeError("Invalid bundle accepted: " + label)

        target_files = restore(bundle, digest, "target", "initial-restore")
        sql("target-quarantine-write-denied", "target", "SELECT 1;", role="target_writer",
            expected='role "target_writer" is not permitted to log in')
        sql("cross-tenant-relationship-denied", "target",
            "INSERT INTO attachments VALUES ('tenant_b', 'foreign', 'tenant_a_permit_1', 'invalid', repeat('0',64), 0, '0640');",
            expected='violates foreign key constraint "attachments_tenant_id_permit_id_fkey"')
        verify_data("target", target_files, baseline, "after-negative-relationship")

        # Pre-write return: target has never had its fixture login enabled. A real
        # accepted source write proves source service return within this fixture.
        check("pre-return-target-never-enabled", not any(b["database"] == "target" and b["fixture_writer_enabled"] for b in state["boundaries"]))
        gate("source", True)
        sql("pre-target-write-source-return", "source",
            "INSERT INTO write_markers VALUES ('source_return_write', 'tenant_a', 'Accepted after pre-target-write return');", role="source_writer")
        check("source-return-write-observed", sql("source-return-readback", "source", "SELECT count(*) FROM write_markers WHERE marker='source_return_write';"), "1")
        gate("source", False)

        # Start the final attempt from a fresh capture including that accepted source write.
        final_bundle, final_digest, final_baseline = capture("source", files, "final-capture")
        sql("discard-quarantined-target", "postgres", "DROP DATABASE target;")
        shutil.rmtree(target_files)
        target_files = restore(final_bundle, final_digest, "target", "final-restore")
        gate("target", True)
        known = target_files / "tenant_a/known-target-write.txt"
        known.write_bytes(b"Known accepted target attachment; must survive post-write recovery.\n")
        known.chmod(0o640)
        sql("known-target-write", "target",
            "BEGIN; INSERT INTO permits VALUES ('tenant_a', 'known_target_permit', 'Known target write', 'approved'); "
            f"INSERT INTO attachments VALUES ('tenant_a', 'known_target_attachment', 'known_target_permit', 'tenant_a/known-target-write.txt', '{sha(known)}', {known.stat().st_size}, '0640'); "
            "INSERT INTO write_markers VALUES ('known_target_write', 'tenant_a', 'Must survive clean-database recovery'); COMMIT;", role="target_writer")
        state["boundaries"].append({"at": now(), "database": "target", "known_target_write_accepted": True, "marker": "known_target_write"})
        gate("target", False)
        sql("retained-source-still-denied", "source", "SELECT 1;", role="source_writer",
            expected='role "source_writer" is not permitted to log in')
        check("retained-source-lacks-target-write", sql("retained-source-marker", "source", "SELECT count(*) FROM write_markers WHERE marker='known_target_write';"), "0")
        recovery_bundle, recovery_digest, after_target = capture("target", target_files, "post-write-capture")
        check("known-target-write-captured", any(m["marker"] == "known_target_write" for m in after_target["write_markers"]))
        recovered_files = restore(recovery_bundle, recovery_digest, "recovery", "post-write-recovery")
        gate("recovery", True)
        check("known-target-write-recovered", sql("recovered-known-write", "recovery", "SELECT count(*) FROM write_markers WHERE marker='known_target_write';", role="recovery_writer"), "1")
        sql("recovered-service-write", "recovery", "INSERT INTO write_markers VALUES ('recovery_write', 'tenant_b', 'Accepted on recovered database');", role="recovery_writer")
        check("recovery-new-write-observed", sql("recovery-new-write-readback", "recovery", "SELECT count(*) FROM write_markers WHERE marker='recovery_write';"), "1")
        check("recovery-known-attachment-preserved", sha(recovered_files / "tenant_a/known-target-write.txt"), sha(known))
        gate("recovery", False)
        state["result"] = "PASS"
        state["native_experiments"] = "NOT_RUN"
        state["acceptance"] = "NOT_REVIEWED"
    except Exception as error:
        state["result"] = "FAIL"
        state["error"] = f"{type(error).__name__}: {error}"
        print(state["error"], flush=True)
    finally:
        if container_started:
            command("postgres-final-log", ["docker", "logs", container_name], cleanup=True, timeout=30)
            command("cleanup-postgres", ["docker", "rm", "-f", "-v", container_name], cleanup=True, timeout=30)
            if state["commands"][-1]["exit_code"]:
                state["result"] = "FAIL"
                state["cleanup"] = "FAILED"
            else:
                state["cleanup"] = "CONTAINER_AND_DISPOSABLE_DATA_REMOVED"
        state["finished_at"] = now()
        state["evidence_sha256"] = {p.name: sha(p) for p in sorted(evidence.iterdir()) if p.is_file() and p.name != "report.json"}
        save()
    return 0 if state["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
