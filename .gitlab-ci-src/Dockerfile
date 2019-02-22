FROM archlinux/base

ENV CCACHE_DIR=/cache/ccache

RUN mkdir /cache
VOLUME /cache

RUN pacman -Syu --noconfirm python-pipenv cmake ninja git gcc which openssh

COPY . /workspace

WORKDIR /workspace

RUN ln -s .gitlab-ci-src/.ws-config.toml

# RUN ./ws build