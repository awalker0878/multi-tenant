# Independent development images

`components.json` records the implemented Python image boundaries: Planning, Inventory, Lifecycle and the separately packaged Inventory and Lifecycle worker bootstraps. Each owns its Dockerfile, package manifest and lock. `inputs.lock.json` records the exact Python and uv child-manifest digests already observed in the accepted P00 development baseline. Product builds read this local lock and their own source; they never copy or import spike implementation.

These images currently run one diagnostic process and exit. Liveness means only that the installed package loaded. Readiness exits 1 because service or worker dependencies are not implemented; unknown arguments exit 2. `HEALTHCHECK NONE` prevents a one-shot process probe from claiming a persistent service is healthy. No server port, task consumer, Temporal worker, native adapter or business operation is started.

## Build and inspect one component

Use a clean checkout of the recorded revision, Linux amd64, Docker with Buildx, and Python 3.11 or later for the standard-library recorder. The image interpreter itself is pinned to Python 3.12.14. Docker must be able to pull the two locked public image references and the builder must reach the package URLs in the component's uv lock. This is a connected development build; it does not prove a disconnected mirror or an operating registry.

From the repository root:

```sh
python3 scripts/p01/run_images.py --component planning --validate-only
python3 scripts/p01/run_images.py \
  --component planning \
  --source-revision "$(git rev-parse HEAD)" \
  --output /tmp/planning-image-evidence
```

The output path must not already exist. Replace `planning` with any exact component ID in the registry. The recorder checks manifest identities and immutable bases, copies only the component's declared build inputs into an otherwise empty directory, builds the `runtime` target and deletes the copied source before the runtime probes. A repository-root build context, sibling source mount and global Python package installation are unnecessary. Local build metadata, tests and retained verification evidence are excluded from the image context.

The builder installs only the exact locked build-tool group, produces a wheel without another dependency resolution, and installs that wheel without dependencies into a fresh virtual environment. The runtime stage contains the measured Python base and that installed environment; it does not receive the builder's uv executable, quality tools, source directory or dependency cache. The upstream Python image still contains its own standard tools; this is not a claim of complete image minimization or a vulnerability assessment.

Every runtime probe uses the image's default UID/GID 10001, a read-only root, no network, all capabilities dropped, no new privileges and bounded process/memory/CPU limits. The isolation probe inspects those actual process properties, the interpreter version, installed distribution inventory and imported module path. It requires only the owning distribution in the virtual environment. The diagnostic remains deliberately unavailable for readiness under these same constraints.

## Evidence and limits

The [image workflow](../../.github/workflows/p01-images.yml) runs each component separately. Each report records the exact Git source revision, SHA-256 of copied source and control files, base-image identities, command arguments, elapsed times, exit outcomes, raw stdout/stderr hashes, image configuration digest and runtime inventory. Expected readiness and invalid-input failures are asserted rather than suppressed. Failed build/probe logs are retained with the report. The workflow uploads evidence for 14 days; accepted permanent evidence is retained and indexed through the implementation register after examination.

An image configuration digest identifies the locally loaded image; it is not a pushed registry manifest digest or an OCI signature. The workflow does not publish images. SBOM generation, advisory scanning, signed publication, promotion controls, persistent service readiness and integration deployment remain their P01 work packages. Building these Python bootstraps alone does not pass G01.01: the four Laravel application images and complete source/contract boundary checks are also required.

## Changing a build input

Change an owning package manifest and lock together and run its source-quality checks before the image workflow. A new runtime dependency requires changing the installation and inventory rules; the recorder refuses to silently omit it. A base-image update requires an explicit candidate measurement and a reviewed update of this input lock and affected Dockerfile defaults. Do not replace digest pins with moving tags, resolve new bases during ordinary replay, or reuse evidence from a different source or lock. A release manifest will eventually compose accepted immutable service identities; this development registry is a build-input declaration, not that release authorization.
