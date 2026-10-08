ARG GO_IMAGE
FROM ${GO_IMAGE} AS build
ARG BINARY=minio
ARG SOURCE_SHA256
WORKDIR /source
COPY source.tar.gz /tmp/source.tar.gz
ENV CGO_ENABLED=0 GOTOOLCHAIN=local
RUN echo "${SOURCE_SHA256}  /tmp/source.tar.gz" | sha256sum -c - && tar -xzf /tmp/source.tar.gz --strip-components=1 && go build -mod=readonly -trimpath -o /out/${BINARY} . && go version -m /out/${BINARY} > /out/build-info.txt && sha256sum go.mod go.sum > /out/module-digests.txt
FROM docker.io/library/python@sha256:1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a
ARG SOURCE_REVISION
ARG BINARY=minio
LABEL io.product.component="source-built-${BINARY}-fixture" org.opencontainers.image.revision="${SOURCE_REVISION}" org.opencontainers.image.licenses="AGPL-3.0-only"
COPY --from=build /out/ /usr/local/bin/
COPY --from=build /source/LICENSE /usr/share/licenses/fixture/LICENSE
RUN mkdir /data && chown 10001:10001 /data && chmod 0700 /data
USER 10001:10001
ENTRYPOINT ["/usr/local/bin/minio"]
