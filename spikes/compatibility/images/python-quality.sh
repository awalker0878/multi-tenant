#!/bin/sh
set -eu
python -c 'import sys; assert sys.version_info[:3] == (3, 12, 14), sys.version; print(sys.version)'
uv_version=$(uv --version)
printf '%s\n' "$uv_version"
case "$uv_version" in 'uv 0.12.19'*) ;; *) exit 1 ;; esac
uv sync --locked --offline --no-managed-python
ruff check .
ruff format --check .
mypy
pytest -q
lint-imports --config .importlinter --no-cache --no-logo
python boundary_probe.py
python smoke.py
