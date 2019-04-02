FROM archlinux/base

ENV CCACHE_DIR=/ccache

RUN mkdir /cache
VOLUME /cache

RUN mkdir /ccache
VOLUME /ccache

RUN pacman -Syu --noconfirm python-pipenv cmake ninja git gcc which openssh lld ccache bison flex rsync make wget awk gperftools diffutils pbzip2

COPY . /workspace

WORKDIR /workspace

RUN ln -s .gitlab-ci-src/.ws-config.toml

RUN git config --global pack.threads "8"