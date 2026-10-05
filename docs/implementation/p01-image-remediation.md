# P01 image admission remediation

Scope: P01.04, BL-P01-002, G01.04. The original Bookworm failures remain
historical evidence. The remediated development candidates now pass the required
checks documented below. No severity threshold, scanner finding or missing fixed
version was converted into an exception.

The first observation compares official Debian trixie and Alpine 3.24 images at
the existing Python 3.12.14 and PHP 8.5.11 language versions. It resolves the exact
linux/amd64 child manifests and scans those immutable references using the pinned
Trivy tool and one recorded advisory database. Results are retained separately
from product image and runtime qualification.

Run 37271464232 at `50b5362dad2ec3686fd9ce433978d081bd4e6c95` measured zero
blocking or secret findings in both Alpine 3.24.2 bases. Trixie still reports
167 blocking matches for PHP and 53 for Python. The [retained report](../../verification/p01/image-remediation/run-37271464232/report.json)
contains the exact manifest identities, scanner/database hashes and findings.

The nine product Dockerfiles now select the two observed Alpine child manifests.
PHP's [APK closure](../../deploy/build/alpine-packages.lock.json) fixes all 76
artifacts by official URL, version, byte size and SHA-256, including five runtime
packages. Each isolated PHP context owns an identical copy. Downloads are checked
before an offline APK install verifies Alpine signatures. Build compilers, headers
and downloaded archives are removed from runtime images. Python installs its
locked wheel graph with binary-only dependencies on the pinned musl base.
The input validator rejects altered, incomplete or ambiguous APK closures.

Use these observations to select a replacement, record all package/build changes,
then rebuild and exercise all affected package, image, Compose, Kubernetes,
messaging and recovery paths before claiming the image blocker is resolved.
Changing the Linux distribution does not establish compatibility by itself.

Primary selection sources: [official Python variants](https://hub.docker.com/_/python)
and [official PHP variants](https://hub.docker.com/_/php). The
[Debian CVE-2023-45853 record](https://security-tracker.debian.org/tracker/CVE-2023-45853)
also demonstrates why package findings need examination: source-package records
can describe code not built into the installed binary. That example does not
waive this candidate set or replace exact-artifact evidence.

The first full PHP rebuild (run 37272257487) rejected an incomplete OpenSSL
upgrade closure. The [retained failed build](../../verification/p01/image-remediation/run-37272257487/catalogue-build.zip)
records the conflict; it was not bypassed. Run 37272419641 then included the
matching OpenSSL executable and successfully installed each build/runtime/Composer
group into the exact base with networking disabled. Its [full observation](../../verification/p01/image-remediation/run-37272419641/report.json)
and package-resolution/install logs are retained separately from the initial comparison.

## Passing full-image and runtime requalification

EV-P01-024–027 bind source `b7705eef994c50863d87b4d8f9ff272f9397ca37`. Run 37272826276 admits all
nine development candidates with zero blocking image/source findings; all nine
build/probe jobs pass. Every pair of image/source SBOMs is CycloneDX and nonempty,
and its hash remains in the signed manifest. Nine signatures, 63 expected denials
and nine unchanged-byte development transfers pass. No risk exception was added.

The affected runtime suite also passes: 179 Compose checks, 196 Kubernetes
checks, 35 messaging checks/16 event fixtures, 28 HTTP fixtures, 40 stateful checks,
79 Permit Desk checks, all package checks and 59 policy-control tests. Both runtime
campaigns retain baseline resource measurements before/after recovery. The exact
9,806-file repository scan reports zero secrets. Detailed records remain in the
[image retrieval](../../verification/p01/artifact-trust/run-37272826276/retrieval.json),
[resource record](p01-resource-observation.md), and [supplementary archives](../../verification/p01/requalification/b7705eef994c50863d87b4d8f9ff272f9397ca37/retrieval.json).

BL-P01-002 is resolved for this development set. [The candidate manifest](../../release/p01-candidate-set.json)
requires independent qualification and does not authorize promotion. Actual review
identities/protection, OP01–OP07 inputs, remaining correlated signal integration
and independent G01 receiving decisions remain outstanding.
