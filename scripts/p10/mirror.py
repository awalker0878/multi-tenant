"""Verify a declared restricted-install closure without downloading or extracting files."""

from evidence import digest, require


def verify_closure(root, manifest, expected_components):
    require(
        set(manifest) == {"candidate_sha256", "components", "artifacts"},
        "invalid_mirror_manifest",
    )
    require(
        isinstance(expected_components, list)
        and expected_components
        and set(manifest["components"]) == set(expected_components)
        and len(manifest["components"]) == len(set(expected_components)),
        "incomplete_mirror_components",
    )
    artifacts = manifest["artifacts"]
    require(isinstance(artifacts, list) and artifacts, "empty_mirror")
    paths, covered = set(), set()
    kinds = {"image", "lock", "sbom", "provenance", "signature", "trust_root"}
    for artifact in artifacts:
        require(
            set(artifact) == {"component", "kind", "path", "sha256", "bytes"},
            "invalid_mirror_artifact",
        )
        require(
            artifact["path"] not in paths
            and artifact["component"] in expected_components
            and artifact["kind"] in kinds,
            "ambiguous_mirror_artifact",
        )
        paths.add(artifact["path"])
        require(
            type(artifact["bytes"]) is int and 0 < artifact["bytes"] <= 16 * 1024**3,
            "mirror_size_bound",
        )
        # Image layers are streamed, not loaded into memory or extracted.
        from pathlib import Path

        from evidence import bounded_file as checked

        if artifact["kind"] == "image":
            from hashlib import file_digest
            from pathlib import PurePosixPath

            p = PurePosixPath(artifact["path"])
            base = Path(root).resolve()
            path = base / p
            require(
                str(p) == artifact["path"]
                and not p.is_absolute()
                and ".." not in p.parts
                and "\\" not in artifact["path"]
                and path.resolve().is_relative_to(base)
                and not any(q.is_symlink() for q in (path, *path.parents))
                and path.is_file()
                and path.stat().st_size == artifact["bytes"],
                "invalid_mirror_image",
            )
            with path.open("rb") as stream:
                actual = file_digest(stream, "sha256").hexdigest()
        else:
            raw = checked(root, artifact["path"])
            require(len(raw) == artifact["bytes"], "mirror_size_changed")
            actual = digest(raw)
        require(actual == artifact["sha256"], "mirror_digest_changed")
        covered.add((artifact["component"], artifact["kind"]))
    require(
        covered == {(c, k) for c in expected_components for k in kinds},
        "mirror_dependency_closure_incomplete",
    )
    return {
        "status": "BYTES_VERIFIED",
        "artifacts": len(paths),
        "network_requests": 0,
        "signature_trust_established": False,
        "installation_qualified": False,
    }
