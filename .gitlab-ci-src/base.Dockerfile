FROM kleenet.comsys.rwth-aachen.de/symbiosys-projects-workspace-docker-base-image:rust

RUN pacman -Syu --noconfirm crypto++ && pacman -Scc --noconfirm

RUN \
	mkdir -p /reference-repos/v1/github.com/stp/ && \
	git clone --mirror https://github.com/stp/minisat.git /reference-repos/v1/github.com/stp/minisat && \
	git -C /reference-repos/v1/github.com/stp/minisat gc --aggressive && \
	git clone --mirror https://github.com/stp/stp.git /reference-repos/v1/github.com/stp/stp && \
	git -C /reference-repos/v1/github.com/stp/stp gc --aggressive && \
	mkdir -p /reference-repos/v1/github.com/klee/ && \
	git clone --mirror https://github.com/klee/klee-uclibc.git /reference-repos/v1/github.com/klee/klee-uclibc && \
	git -C /reference-repos/v1/github.com/klee/klee-uclibc gc --aggressive

COPY . /workspace
