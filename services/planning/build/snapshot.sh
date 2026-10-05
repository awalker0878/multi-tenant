#!/bin/sh
set -eu
# The snapshot retains signed Release metadata and package hashes. Only its
# intentionally historical Valid-Until timestamp is disabled, never authentication.
case "$DEBIAN_SNAPSHOT" in
    20261004T000000Z) ;;
    *) echo 'Unapproved Debian snapshot; expected 20261004T000000Z' >&2; exit 1 ;;
esac
rm -f /etc/apt/sources.list /etc/apt/sources.list.d/*
cat > /etc/apt/sources.list.d/service-snapshot.sources <<SOURCES
Types: deb
URIs: https://snapshot.debian.org/archive/debian/$DEBIAN_SNAPSHOT/
Suites: bookworm bookworm-updates
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
Check-Valid-Until: no

Types: deb
URIs: https://snapshot.debian.org/archive/debian-security/$DEBIAN_SNAPSHOT/
Suites: bookworm-security
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
Check-Valid-Until: no
SOURCES
