ARG PHP_BASE=docker.io/library/php@sha256:aba7168955e4b1e1f5e61e2e5a0257eff5b1563d3fc4ca272373183b57f53005
ARG COMPOSER_BASE=docker.io/library/composer@sha256:bdd249749908be12facc9dec72e19704371bb893f96dff3e024ec89528a5a08d
FROM ${COMPOSER_BASE} AS composer-tool

FROM ${PHP_BASE} AS php-base
COPY build/download-apks.php build/apk.lock.json /tmp/service-build/
RUN : > /etc/apk/repositories \
    && php /tmp/service-build/download-apks.php build \
    && apk add --no-network --repositories-file /dev/null --virtual .phpize-deps /tmp/service-apks/*.apk \
    && docker-php-ext-install -j2 pdo_pgsql \
    && apk add --no-network --repositories-file /dev/null libpq=18.6-r0 openssl=3.5.9-r0 \
    && apk del --no-network .phpize-deps \
    && rm -rf /tmp/service-apks /tmp/service-build \
    && cp "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"
WORKDIR /app

FROM php-base AS dependencies
COPY --from=composer-tool /usr/bin/composer /usr/local/bin/composer
COPY build/download-apks.php build/apk.lock.json /tmp/service-build/
RUN php /tmp/service-build/download-apks.php composer \
    && apk add --no-network --repositories-file /dev/null /tmp/service-apks/*.apk \
    && rm -rf /tmp/service-apks /tmp/service-build
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
LABEL io.product.component="assurance"
LABEL org.opencontainers.image.revision=$SOURCE_REVISION
COPY --from=dependencies /app/vendor/ ./vendor/
COPY --from=dependencies /app/app/ ./app/
COPY --from=dependencies /app/bootstrap/ ./bootstrap/
COPY --from=dependencies /app/config/ ./config/
COPY --from=dependencies /app/public/ ./public/
COPY --from=dependencies /app/routes/ ./routes/
COPY --from=dependencies /app/artisan /app/composer.json /app/composer.lock ./
COPY --from=dependencies /app/resources/ ./resources/
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
