# Build context is this component directory only. Inputs are accepted development candidates.
ARG PYTHON_BASE=docker.io/library/python@sha256:9b8dad7f66b5c7751df6cb7a64a07812e86bed85d0116efe82b3a11209f1440d
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
ARG SOURCE_REVISION=unrecorded
LABEL io.product.component="lifecycle"
LABEL org.opencontainers.image.title="product-lifecycle bootstrap" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.source="https://github.com/awalker0878/multi-tenant"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/opt/venv/bin:$PATH
WORKDIR /app
COPY --from=build /opt/venv/ /opt/venv/
USER 10001:10001
# The default remains a one-shot process diagnostic. Development Compose selects
# the separately installed service-owned ASGI entrypoint and private port 8080.
HEALTHCHECK NONE
ENTRYPOINT ["/opt/venv/bin/lifecycle-health"]
CMD ["liveness"]
