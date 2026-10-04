ARG PHP_BASE=docker.io/library/php@sha256:c0dc98639fddeaad891a338e1e3fa2b2d724eb616bcd5a0bb1d8afd650e0fda3
ARG COMPOSER_BASE=docker.io/library/composer@sha256:bdd249749908be12facc9dec72e19704371bb893f96dff3e024ec89528a5a08d
ARG NODE_BASE=docker.io/library/node@sha256:e5a8dee7bc1e6a215d224a7ef8206f7e77271bc3cabd5febf2beafac0674f174
FROM ${COMPOSER_BASE} AS composer-tool
FROM ${NODE_BASE} AS frontend
WORKDIR /frontend
COPY package.json package-lock.json tsconfig.json vite.config.ts ./
COPY resources/ ./resources/
RUN node -e 'if (process.version !== "v24.19.0") throw new Error(process.version)' \
    && npm --version \
    && npm ci --ignore-scripts --no-audit --no-fund \
    && npm run typecheck && npm run build

FROM ${PHP_BASE} AS php-base
ARG DEBIAN_SNAPSHOT=20261004T000000Z
COPY build/snapshot.sh /tmp/service-snapshot.sh
RUN sh /tmp/service-snapshot.sh \
    && apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev \
    && docker-php-ext-install -j2 pdo_pgsql \
    && apt-mark manual libpq5 \
    && apt-get purge -y --auto-remove libpq-dev $PHPIZE_DEPS \
    && rm -rf /var/lib/apt/lists/* /tmp/service-snapshot.sh \
    && cp "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"
WORKDIR /app

FROM php-base AS dependencies
COPY --from=composer-tool /usr/bin/composer /usr/local/bin/composer
RUN apt-get update && apt-get install -y --no-install-recommends unzip \
    && rm -rf /var/lib/apt/lists/*
COPY . ./
ENV COMPOSER_ALLOW_SUPERUSER=1
# Require a matching private lock; exact version pins are deliberate.
RUN composer --version \
    && composer validate --strict --no-check-all \
    && composer install --no-dev --no-plugins --no-scripts --no-interaction \
        --prefer-dist --no-progress --classmap-authoritative \
    && composer check-platform-reqs --no-dev \
    && mkdir -p resources bootstrap/cache

FROM php-base AS php-runtime
ARG SOURCE_REVISION
LABEL io.product.component="console"
LABEL org.opencontainers.image.revision=$SOURCE_REVISION
COPY --from=dependencies /app/vendor/ ./vendor/
COPY --from=dependencies /app/app/ ./app/
COPY --from=dependencies /app/bootstrap/ ./bootstrap/
COPY --from=dependencies /app/config/ ./config/
COPY --from=dependencies /app/public/ ./public/
COPY --from=dependencies /app/routes/ ./routes/
COPY --from=dependencies /app/artisan /app/composer.json /app/composer.lock ./
COPY --from=dependencies /app/resources/views/ ./resources/views/
# Inertia validates server-side page existence before returning the compiled page.
COPY --from=dependencies /app/resources/js/pages/ ./resources/js/pages/
COPY --from=frontend /frontend/public/build/ ./public/build/
# These directories are the only application paths that require writable mounts.
# No application key or deployment configuration is generated during the build.
RUN mkdir -p bootstrap/cache storage/framework/cache storage/framework/sessions storage/framework/views storage/logs \
    && chown -R 10001:10001 bootstrap/cache storage \
    && printf '[global]\npid = /tmp/php-fpm.pid\n[www]\nlisten = 9000\nclear_env = no\n' > /usr/local/etc/php-fpm.d/zz-service.conf \
    && printf '%s\n' '#!/bin/sh' 'set -eu' \
        'mkdir -p /app/bootstrap/cache /app/storage/framework/cache /app/storage/framework/sessions /app/storage/framework/views /app/storage/logs' \
        'exec docker-php-entrypoint "$@"' > /usr/local/bin/service-entrypoint \
    && chmod 0755 /usr/local/bin/service-entrypoint
USER 10001:10001
ENV APP_ENV=production APP_DEBUG=false
ENTRYPOINT ["/usr/local/bin/service-entrypoint"]
CMD ["php-fpm", "-F"]
