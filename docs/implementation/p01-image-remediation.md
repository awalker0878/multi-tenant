# P01 image admission remediation

Scope: P01.04, BL-P01-002, G01.04. The existing nine candidates stay HELD until
actual replacement artifacts pass the required checks. No severity threshold,
scanner finding or missing fixed version is converted into an exception.

The first observation compares official Debian trixie and Alpine 3.24 images at
the existing Python 3.12.14 and PHP 8.5.11 language versions. It resolves the exact
linux/amd64 child manifests and scans those immutable references using the pinned
Trivy tool and one recorded advisory database. Results are retained separately
from product image and runtime qualification. The candidate list does not change
the adopted build lock or product Dockerfiles.

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
