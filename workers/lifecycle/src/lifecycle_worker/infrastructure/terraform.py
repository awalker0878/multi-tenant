"""Pinned Terraform saved-plan adapter. No init, replan, force-unlock or destroy command."""

import hashlib
import os
import re
import signal
import subprocess
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lifecycle_worker.application.native import (
    RESOURCE_TYPES,
    NativeBinding,
    NativeHeld,
    ProcessResult,
    decode,
    digest,
)
from lifecycle_worker.infrastructure.native_files import (
    protected_read,
    relative_file,
    verify_bundle,
)


def run(
    argv: list[str],
    root: Path,
    environment: dict[str, str],
    timeout: float,
    heartbeat: Callable[[], None],
    limit: int = 2_097_152,
) -> tuple[ProcessResult, bytes]:
    """Run without a shell; private bounded output is never printed or added to receipts."""
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        heartbeat()
        process = subprocess.Popen(
            argv,
            cwd=root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
        deadline = time.monotonic() + timeout
        interrupted = False
        try:
            while process.poll() is None:
                heartbeat()
                if time.monotonic() >= deadline or any(
                    os.fstat(f.fileno()).st_size > limit for f in (stdout, stderr)
                ):
                    raise NativeHeld("native_process_bound")
                time.sleep(0.05)
        except BaseException:
            interrupted = True
        finally:
            if interrupted:
                # Kill the complete provider process group before returning. Uncertain effects
                # remain held even when the OS confirms process death.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait()
        stdout.seek(0)
        raw = stdout.read(limit + 1)
        if len(raw) > limit or os.fstat(stderr.fileno()).st_size > limit:
            interrupted = True
            raw = b""
        return ProcessResult(process.returncode, interrupted), raw


class TerraformSavedPlan:
    def __init__(
        self,
        executable: Path,
        root: Path,
        public_environment: dict[str, str],
        credential_files: dict[str, Path],
    ) -> None:
        self.executable, self.root = executable, root
        self.public_environment, self.credential_files = public_environment, credential_files

    def verified(self, binding: NativeBinding) -> dict[str, Any]:
        manifest = verify_bundle(self.root, binding.bundle_sha256)
        if (
            hashlib.sha256(protected_read(self.executable, 268_435_456)).hexdigest()
            != manifest["terraform_sha256"]
            or digest(self.public_environment) != manifest["environment_sha256"]
            or not isinstance(manifest["terraform_version"], str)
            or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", manifest["terraform_version"]) is None
        ):
            raise NativeHeld("native_toolchain_changed")
        return manifest

    def environment(self, binding: NativeBinding) -> dict[str, str]:
        allowed = {
            "OS_AUTH_URL",
            "OS_AUTH_TYPE",
            "OS_REGION_NAME",
            "OS_INTERFACE",
            "OS_CACERT",
            "OS_PROJECT_ID",
            "OS_USER_DOMAIN_ID",
            "OS_PROJECT_DOMAIN_ID",
            "OS_IDENTITY_API_VERSION",
            "OS_COMPUTE_API_VERSION",
            "OS_VOLUME_API_VERSION",
            "TF_CLI_CONFIG_FILE",
        }
        credentials = {"OS_APPLICATION_CREDENTIAL_ID", "OS_APPLICATION_CREDENTIAL_SECRET"}
        if (
            set(self.public_environment) - allowed
            or set(self.credential_files) != credentials
            or self.public_environment.get("OS_PROJECT_ID") != binding.project_id
            or self.public_environment.get("OS_AUTH_TYPE") != "v3applicationcredential"
            or not self.public_environment.get("OS_AUTH_URL", "").startswith("https://")
            or not self.public_environment.get("OS_CACERT", "").startswith("/")
        ):
            raise NativeHeld("unsafe_terraform_environment")
        # Never inherit TF_CLI_ARGS, proxy overrides, plugin paths, shell hooks or credentials.
        environment = {
            "PATH": "/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "TF_IN_AUTOMATION": "1",
            "TF_INPUT": "0",
            "TF_WORKSPACE": binding.workspace,
            "CHECKPOINT_DISABLE": "1",
            **self.public_environment,
        }
        for name, path in self.credential_files.items():
            raw = protected_read(path, 4096).rstrip(b"\r\n")
            if not raw or any(c < 33 or c > 126 for c in raw):
                raise NativeHeld("invalid_native_credential")
            environment[name] = raw.decode("ascii")
        return environment

    def command(
        self,
        binding: NativeBinding,
        args: list[str],
        heartbeat: Callable[[], None],
        timeout: float = 30,
    ) -> tuple[ProcessResult, bytes]:
        self.verified(binding)
        return run(
            [str(self.executable), *args],
            self.root,
            self.environment(binding),
            timeout,
            heartbeat,
        )

    def read(self, binding: NativeBinding, args: list[str]) -> bytes:
        result, raw = self.command(binding, args, lambda: None)
        if result.exit_code != 0 or result.interrupted:
            raise NativeHeld("terraform_read_unavailable")
        return raw

    def state(self, binding: NativeBinding) -> dict[str, Any]:
        state = decode(self.read(binding, ["state", "pull"]))
        if (
            state.get("version") != 4
            or state.get("lineage") != binding.state_lineage
            or type(state.get("serial")) is not int
            or state["serial"] < binding.state_serial
        ):
            raise NativeHeld("terraform_state_changed")
        return state

    def inspect(self, binding: NativeBinding) -> dict[str, Any]:
        manifest = self.verified(binding)
        version = decode(self.read(binding, ["version", "-json"]))
        if version.get("terraform_version") != manifest["terraform_version"]:
            raise NativeHeld("terraform_version_changed")
        if self.read(binding, ["workspace", "show"]).strip().decode() != binding.workspace:
            raise NativeHeld("terraform_workspace_changed")
        backend = decode(protected_read(self.root / ".terraform/terraform.tfstate", 1_048_576))
        configuration = backend.get("backend", {})
        # HTTP locking is a supported adapter capability, not an installation selection.
        # The exact owner-protected backend bytes remain in the bundle inventory.
        settings = configuration.get("config", {})
        if (
            configuration.get("type") != "http"
            or not all(
                isinstance(settings.get(k), str) and settings[k].startswith("https://")
                for k in ("address", "lock_address", "unlock_address")
            )
            or settings.get("skip_cert_verification", False)
        ):
            raise NativeHeld("qualified_locking_backend_required")
        state = self.state(binding)
        if state["serial"] != binding.state_serial:
            raise NativeHeld("terraform_state_changed")
        plan = decode(
            self.read(
                binding, ["show", "-json", str(relative_file(self.root, manifest["saved_plan"]))]
            )
        )
        if digest(plan) != manifest["plan_json_sha256"]:
            raise NativeHeld("reviewed_plan_changed")
        validate_plan(plan, manifest["resources"], binding)
        return {
            "bundle_sha256": binding.bundle_sha256,
            "plan_json_sha256": manifest["plan_json_sha256"],
            "state_serial": state["serial"],
            "resource_count": len(manifest["resources"]),
        }

    def apply(self, binding: NativeBinding, heartbeat: Callable[[], None]) -> ProcessResult:
        # Repeat artifact/state comparison immediately before the native boundary.
        self.inspect(binding)
        manifest = self.verified(binding)
        result, _ = self.command(
            binding,
            [
                "apply",
                "-input=false",
                "-no-color",
                "-lock=true",
                "-lock-timeout=0s",
                "-parallelism=1",
                str(relative_file(self.root, manifest["saved_plan"])),
            ],
            heartbeat,
            timeout=600,
        )
        return result


def validate_plan(plan: dict[str, Any], resources: Any, binding: NativeBinding) -> None:
    if (
        not isinstance(plan.get("format_version"), str)
        or plan["format_version"].split(".")[0] != "1"
        or plan.get("errored") is not False
        or plan.get("applyable") is not True
        or plan.get("complete") is not True
        or not isinstance(resources, dict)
        or not 1 <= len(resources) <= 128
        or plan.get("resource_drift")
        or plan.get("deferred_changes")
    ):
        raise NativeHeld("unsupported_or_incomplete_native_plan")

    def no_provisioners(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("provisioners"):
                raise NativeHeld("native_provisioner_forbidden")
            for nested in value.values():
                no_provisioners(nested)
        elif isinstance(value, list):
            for nested in value:
                no_provisioners(nested)

    no_provisioners(plan.get("configuration", {}))
    changes = plan.get("resource_changes")
    if not isinstance(changes, list) or len(changes) != len(resources):
        raise NativeHeld("native_resource_set_changed")
    seen: set[str] = set()
    for resource in changes:
        address = resource.get("address")
        change = resource.get("change", {})
        if (
            not isinstance(address, str)
            or address not in resources
            or address in seen
            or resource.get("mode") != "managed"
            or resource.get("provider_name")
            != "registry.terraform.io/terraform-provider-openstack/openstack"
            or resource.get("type") not in RESOURCE_TYPES
            or resource.get("previous_address")
            or resource.get("deposed")
            or change.get("actions") != ["create"]
            or change.get("before") is not None
            or change.get("importing")
        ):
            raise NativeHeld("native_change_outside_initial_provisioning")
        seen.add(address)
        contract = resources[address]
        if (
            not isinstance(contract, dict)
            or set(contract) != {"kind", "expected"}
            or contract["kind"] != RESOURCE_TYPES[resource["type"]]
            or not isinstance(contract["expected"], dict)
        ):
            raise NativeHeld("invalid_native_resource_contract")
        expected = contract["expected"]
        after = change.get("after", {})
        unknown = change.get("after_unknown", {})
        # A review may never claim a known field when Terraform still considers it unknown.
        for field, value in expected.items():
            if after.get(field) != value or unknown.get(field):
                raise NativeHeld("native_expected_field_changed")
        if contract["kind"] in {"server", "volume"}:
            metadata = expected.get("metadata", {})
            if any(
                metadata.get(k) != v
                for k, v in {
                    "product_tenant_id": binding.tenant_id,
                    "product_resource_id": binding.resource_id,
                }.items()
            ):
                raise NativeHeld("native_ownership_marker_missing")
        elif (
            expected.get("description") != f"product:{binding.tenant_id}:{binding.resource_id}"
            or expected.get("port_security_enabled") is not True
            or expected.get("admin_state_up") is not False
            or not expected.get("security_group_ids")
            or expected.get("tenant_id") != binding.project_id
        ):
            raise NativeHeld("native_quarantine_required")
