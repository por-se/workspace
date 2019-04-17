# see https://docs.docker.com/develop/develop-images/dockerfile_best-practices/

FROM archlinux/base

RUN pacman -Syu --noconfirm python-pipenv cmake ninja git gcc which openssh lld ccache bison flex rsync make wget awk gperftools diffutils coreutils && pacman -Scc --noconfirm

RUN mkdir /cache
VOLUME /ccache

RUN mkdir /ccache
VOLUME /cache

ENV CCACHE_DIR=/ccache

COPY . /workspace

WORKDIR /workspace

RUN cp .gitlab-ci-src/.ws-config.toml .