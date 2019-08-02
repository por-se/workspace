FROM archlinux/base
ENV CCACHE_DIR=/ccache
RUN pacman -Syu --noconfirm python-pipenv cmake ninja git gcc which openssh lld ccache bison flex rsync make wget awk gperftools diffutils && pacman -Scc --noconfirm

COPY . /workspace
WORKDIR /workspace
RUN cp .gitlab-ci-src/ws-settings.toml .
RUN ./ws echo "Done"