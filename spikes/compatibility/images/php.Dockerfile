ARG PHP_BASE
ARG COMPOSER_BASE
ARG NODE_BASE
FROM ${COMPOSER_BASE} AS composer-tool
FROM ${NODE_BASE} AS frontend
WORKDIR /frontend
COPY frontend/ ./
RUN node -e 'if (process.version !== "v24.19.0") throw new Error(process.version)' && npm --version \
    && npm ci --ignore-scripts --no-audit --no-fund \
    && npm run typecheck && npm run build

FROM ${PHP_BASE} AS php-base
ARG DEBIAN_SNAPSHOT
COPY images/snapshot.sh /tmp/p00-snapshot.sh
RUN sh /tmp/p00-snapshot.sh \
    && apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev \
    && docker-php-ext-install -j2 pdo_pgsql \
    && apt-mark manual libpq5 \
    && apt-get purge -y --auto-remove libpq-dev $PHPIZE_DEPS \
    && rm -rf /var/lib/apt/lists/* /tmp/p00-snapshot.sh \
    && cp "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"
WORKDIR /app

FROM php-base AS dependencies
COPY --from=composer-tool /usr/bin/composer /usr/local/bin/composer
RUN apt-get update && apt-get install -y --no-install-recommends unzip \
    && rm -rf /var/lib/apt/lists/*
COPY php/ ./
ENV COMPOSER_ALLOW_SUPERUSER=1
RUN composer install --no-dev --no-plugins --no-scripts --no-interaction --prefer-dist --no-progress --classmap-authoritative \
    && composer check-platform-reqs --no-dev

FROM php-base AS php-quality
COPY --from=composer-tool /usr/bin/composer /usr/local/bin/composer
RUN apt-get update && apt-get install -y --no-install-recommends python3 unzip \
    && rm -rf /var/lib/apt/lists/*
COPY php/ ./
COPY frontend/resources/js/Pages/ /frontend/resources/js/Pages/
COPY images/php-quality.sh /opt/p00/php-quality.sh
ENV COMPOSER_ALLOW_SUPERUSER=1
RUN composer install --no-scripts --no-interaction --prefer-dist --no-progress \
    && printf '# Disposable P00 fixture; test runner supplies configuration.\n' > .env \
    && mkdir -p bootstrap/cache storage/framework/cache storage/framework/sessions storage/framework/views storage/logs \
    && chown -R 10001:10001 /app
USER 10001:10001
ENV COMPOSER_HOME=/tmp/p00-composer APP_ENV=testing
CMD ["sh", "/opt/p00/php-quality.sh"]

FROM php-base AS php-runtime
COPY --from=dependencies /app/vendor ./vendor
COPY php/app/ ./app/
COPY php/bootstrap/ ./bootstrap/
COPY php/config/ ./config/
COPY php/public/ ./public/
COPY php/resources/ ./resources/
COPY php/routes/ ./routes/
COPY frontend/resources/js/Pages/ /frontend/resources/js/Pages/
COPY php/artisan php/composer.json php/composer.lock ./
COPY --from=frontend /frontend/public/build/ ./public/build/
RUN printf '# Disposable fixture: runtime configuration must be injected.\n' > .env \
    && mkdir -p bootstrap/cache storage/framework/cache storage/framework/sessions storage/framework/views storage/logs \
    && chown -R 10001:10001 bootstrap/cache storage \
    && printf '[global]\npid = /tmp/php-fpm.pid\n[www]\nlisten = 9000\n' > /usr/local/etc/php-fpm.d/zz-p00.conf
USER 10001:10001
ENV APP_ENV=production APP_DEBUG=false
CMD ["php-fpm", "-F"]
