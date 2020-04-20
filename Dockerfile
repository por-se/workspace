FROM archlinux/base

RUN echo LC_ALL=en_US.UTF-8 >>/etc/locale.conf && \
		mv /usr/share/libalpm/hooks/package-cleanup.hook /tmp/package-cleanup.hook && \
		\
		pacman -Syu --noconfirm base python-pipenv cmake ninja git gcc which openssh lld ccache bison flex rsync make wget awk gperftools diffutils moreutils time patch file fish zsh && \
		\
		pacman -S --noconfirm bleachbit && \
		bleachbit --clean 'system.localizations' && \
		pacman -Rs --noconfirm bleachbit && \
		\
		rm -rf usr/lib/python*/test && \
		rm -rf /var/lib/pacman/sync/* && \
		mv /tmp/package-cleanup.hook /usr/share/libalpm/hooks/package-cleanup.hook

ADD . /workspace

RUN /workspace/ws build

ENTRYPOINT ["/workspace/ws"]
CMD ["shell", "-s", "fish"]
