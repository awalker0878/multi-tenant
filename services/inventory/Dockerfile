# Build context is this component directory only. Inputs are accepted development candidates.
ARG PYTHON_BASE=docker.io/library/python@sha256:1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a
ARG UV_BASE=ghcr.io/astral-sh/uv@sha256:d46db4c7b7f2e75ff80aeef95da4c2c6ff1ad399c13ab85067db4430b7c3b9c3
FROM ${UV_BASE} AS uv-tool
FROM ${PYTHON_BASE} AS build
COPY --from=uv-tool /uv /usr/local/bin/uv
WORKDIR /build
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1
COPY .python-version pyproject.toml uv.lock README.md ./
COPY src/ ./src/
RUN uv sync --locked --only-group build --no-install-project --no-managed-python \
    && uv build --offline --no-build-isolation --wheel \
    && uv export --locked --no-default-groups --no-emit-project --no-annotate --no-header \
         --format requirements.txt --output-file /build/production-requirements.txt \
    && uv venv --no-managed-python --python /usr/local/bin/python /opt/venv \
    && uv pip sync --python /opt/venv/bin/python --require-hashes --only-binary :all: /build/production-requirements.txt \
    && uv pip install --python /opt/venv/bin/python --offline --no-index --no-deps dist/*.whl \
    && uv pip check --python /opt/venv/bin/python

FROM ${PYTHON_BASE} AS runtime
ARG DEBIAN_SNAPSHOT=20261004T000000Z
COPY build/snapshot.sh /tmp/service-snapshot.sh
RUN sh /tmp/service-snapshot.sh \
    && apt-get update \
    && apt-get install -y --no-install-recommends libpcre2-8-0=10.42-1+deb12u2 tzdata=2026c-0+deb12u1 \
    && rm -rf /var/lib/apt/lists/* /tmp/service-snapshot.sh
ARG SOURCE_REVISION=unrecorded
LABEL io.product.component="inventory"
LABEL org.opencontainers.image.title="product-inventory bootstrap" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.source="https://github.com/awalker0878/multi-tenant"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/opt/venv/bin:$PATH
WORKDIR /app
COPY --from=build /opt/venv/ /opt/venv/
USER 10001:10001
# The default remains a one-shot process diagnostic. Development Compose selects
# the separately installed service-owned ASGI entrypoint and private port 8080.
HEALTHCHECK NONE
ENTRYPOINT ["/opt/venv/bin/inventory-health"]
CMD ["liveness"]
