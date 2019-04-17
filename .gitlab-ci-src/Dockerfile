# see ttps://docs.docker.com/develop/develop-images/dockerfile_best-practices/

FROM archlinux/base

ENV CCACHE_DIR=/ccache

RUN mkdir /cache
VOLUME /cache

RUN mkdir /ccache
VOLUME /ccache

RUN pacman -Syu --noconfirm python-pipenv cmake ninja git gcc which openssh lld ccache bison flex rsync make wget awk gperftools diffutils

RUN git config --global pack.threads "8"

COPY . /workspace

WORKDIR /workspace

RUN cp .gitlab-ci-src/.ws-config.toml .