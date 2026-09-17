#!/usr/bin/env bash
set -euo pipefail
version=1.16.3
expected=093b6ae9a2228af5029c41606bc96eb583553528aad1bfe7e0b4d62fc91e25d8
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
curl --fail --silent --show-error --location --retry 2 --connect-timeout 20 --max-time 180 \
  "https://releases.hashicorp.com/terraform/${version}/terraform_${version}_linux_amd64.zip" -o "$work/terraform.zip"
printf '%s  %s\n' "$expected" "$work/terraform.zip" | sha256sum --check --status
mkdir -p "$HOME/.local/bin"
unzip -q "$work/terraform.zip" terraform -d "$work"
install -m 0755 "$work/terraform" "$HOME/.local/bin/terraform"
if [[ -n "${GITHUB_PATH:-}" ]]; then echo "$HOME/.local/bin" >> "$GITHUB_PATH"; fi
"$HOME/.local/bin/terraform" version
