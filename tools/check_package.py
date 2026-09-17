#!/usr/bin/env python3
"""Repository gate; historical guide/report counts no longer stand in for current tests."""
from pathlib import Path
import subprocess
import sys
if __name__ == '__main__':
    raise SystemExit(subprocess.call([sys.executable, str(Path(__file__).resolve().parents[1] / 'scripts/check_repository.py')]))
