FROM mcr.microsoft.com/devcontainers/go:1.22-bullseye
WORKDIR /aws-db-import
USER root

ENV GOPRIVATE=github.com/thegreatforge/*
ENV HOSTNAME=local-devcontainer

RUN sudo apt-get update -y \
    && sudo apt-get install -y --no-install-recommends \
    make automake pkg-config libtool autoconf lsb-release wget

COPY . .
ENTRYPOINT ["sleep", "infinity"]