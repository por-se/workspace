FROM archlinux/base
ENV CCACHE_DIR=/ccache
RUN pacman -Syu --noconfirm python-pipenv cmake ninja git gcc which openssh lld ccache bison flex rsync make wget awk gperftools diffutils crypto++ && pacman -Scc --noconfirm

RUN \
	mkdir -p /reference-repos/v1/github.com/llvm/ && \
	git clone --mirror https://github.com/llvm/llvm-project.git /reference-repos/v1/github.com/llvm/llvm-project && \
	git -C /reference-repos/v1/github.com/llvm/llvm-project gc --aggressive && \
	mkdir -p /reference-repos/v1/github.com/Z3Prover/ && \
	git clone --mirror https://github.com/Z3Prover/z3.git /reference-repos/v1/github.com/Z3Prover/z3 && \
	git -C /reference-repos/v1/github.com/Z3Prover/z3 gc --aggressive && \
	mkdir -p /reference-repos/v1/github.com/stp/ && \
	git clone --mirror https://github.com/stp/minisat.git /reference-repos/v1/github.com/stp/minisat && \
	git -C /reference-repos/v1/github.com/stp/minisat gc --aggressive && \
	git clone --mirror https://github.com/stp/stp.git /reference-repos/v1/github.com/stp/stp && \
	git -C /reference-repos/v1/github.com/stp/stp gc --aggressive && \
	mkdir -p /reference-repos/v1/github.com/klee/ && \
	git clone --mirror https://github.com/klee/klee-uclibc.git /reference-repos/v1/github.com/klee/klee-uclibc && \
	git -C /reference-repos/v1/github.com/klee/klee-uclibc gc --aggressive && \
	git clone --mirror https://github.com/klee/klee.git /reference-repos/v1/github.com/klee/klee && \
	git -C /reference-repos/v1/github.com/klee/klee gc --aggressive

COPY . /workspace
WORKDIR /workspace
