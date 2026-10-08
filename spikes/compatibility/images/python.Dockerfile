ARG PYTHON_BASE
ARG UV_BASE
FROM ${UV_BASE} AS uv-tool
FROM ${PYTHON_BASE} AS python-base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

FROM python-base AS dependencies
COPY --from=uv-tool /uv /usr/local/bin/uv
COPY python/ ./
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
RUN uv --version && uv sync --locked --no-dev --no-managed-python

FROM python-base AS python-quality
COPY --from=uv-tool /uv /usr/local/bin/uv
COPY python/ ./
COPY images/python-quality.sh /opt/p00/python-quality.sh
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
RUN uv sync --locked --no-managed-python && chown -R 10001:10001 /app
USER 10001:10001
ENV UV_CACHE_DIR=/tmp/p00-uv-cache PATH=/app/.venv/bin:$PATH PYTHONPATH=/app/src
CMD ["sh", "/opt/p00/python-quality.sh"]

FROM python-base AS python-runtime
COPY --from=dependencies /app/.venv/ ./.venv/
COPY python/src/ ./src/
COPY python/smoke.py python/pyproject.toml python/uv.lock ./
USER 10001:10001
ENV PATH=/app/.venv/bin:$PATH PYTHONPATH=/app/src
# This is a fixture smoke command, not a service lifecycle or readiness contract.
CMD ["python", "smoke.py"]
