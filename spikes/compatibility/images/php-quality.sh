#!/bin/sh
set -eu
php -r 'if (PHP_VERSION !== "8.5.11") { throw new RuntimeException("Unexpected PHP patch"); } echo PHP_VERSION.PHP_EOL;'
composer_version=$(composer --version --no-ansi)
printf '%s\n' "$composer_version"
case "$composer_version" in 'Composer version 2.10.3 '*) ;; *) exit 1 ;; esac
python3 --version
composer validate --strict --no-interaction
composer check-platform-reqs --no-interaction
php smoke.php
php vendor/bin/pint --test
php vendor/bin/phpstan analyse --no-progress --memory-limit=1G
php vendor/bin/deptrac analyse --no-cache --fail-on-uncovered
php vendor/bin/pest --colors=never --display-warnings --fail-on-warning --fail-on-risky --fail-on-empty-test-suite
python3 tools/verify_quality_canaries.py
