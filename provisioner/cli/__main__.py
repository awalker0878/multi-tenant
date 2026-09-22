"""Module entry point for the provisioning command line.

The active documents name one entry point, `python -m provisioner.cli <command>
<request.yaml>`. This module is that entry point; it delegates to the same
transport `provisioner.cli.main` exposes, so both spellings run identical code and
neither can drift into a second implementation.
"""
from __future__ import annotations

import sys

from provisioner.cli.main import main

if __name__ == '__main__':
    sys.exit(main())