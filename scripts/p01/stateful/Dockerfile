FROM docker.io/library/python@sha256:1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a AS build
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir --require-hashes --only-binary=:all: -r requirements.txt && /opt/venv/bin/pip check
FROM docker.io/library/python@sha256:1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a
ARG SOURCE_REVISION
LABEL io.product.component="stateful-dependency-probe" org.opencontainers.image.revision="${SOURCE_REVISION}"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/opt/venv/bin:$PATH
WORKDIR /probe
COPY --from=build /opt/venv /opt/venv
COPY probe.py workflow.py ./
USER 10001:10001
ENTRYPOINT ["python", "/probe/probe.py"]
