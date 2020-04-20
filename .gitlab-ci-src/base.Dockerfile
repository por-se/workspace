FROM laboratory.comsys.rwth-aachen.de:5050/symbiosys/projects/workspace/docker-base-image:latest

RUN pacman -Syu --noconfirm crypto++ && pacman -Scc --noconfirm

RUN \
	mkdir -p /reference-repos/v1/github.com/stp/ && \
	git clone --mirror https://github.com/stp/minisat.git /reference-repos/v1/github.com/stp/minisat && \
	git -C /reference-repos/v1/github.com/stp/minisat gc --aggressive && \
	git clone --mirror https://github.com/stp/stp.git /reference-repos/v1/github.com/stp/stp && \
	git -C /reference-repos/v1/github.com/stp/stp gc --aggressive

COPY . /workspace
