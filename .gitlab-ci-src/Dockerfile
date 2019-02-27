FROM archlinux/base

ENV CCACHE_DIR=/ccache

RUN mkdir /cache
VOLUME /cache

RUN mkdir /ccache
VOLUME /ccache

RUN pacman -Syu --noconfirm python-pipenv cmake ninja git gcc which openssh lld ccache bison flex rsync make wget awk gperftools diffutils
#  - apt-get update && apt-get install -y bash python3 git g++ ninja-build binutils-gold make cmake ccache zlib1g-dev libboost-program-options-dev bison flex perl python3-distutils libncurses-dev wget python3-pip libcrypto++-dev libgoogle-perftools-dev

COPY . /workspace

WORKDIR /workspace

RUN ln -s .gitlab-ci-src/.ws-config.toml

RUN git config --global pack.threads "8"

# RUN ./ws build