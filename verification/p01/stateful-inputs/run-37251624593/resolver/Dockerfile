FROM docker.io/library/python@sha256:1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a
COPY --from=ghcr.io/astral-sh/uv@sha256:d46db4c7b7f2e75ff80aeef95da4c2c6ff1ad399c13ab85067db4430b7c3b9c3 /uv /usr/local/bin/uv
ENTRYPOINT ["uv"]
