import os
import shutil
import subprocess

import workspace.util as util
from workspace.build_systems.linker import Linker
from workspace.settings import settings


def _run(cmd, *args, **kwargs):
    kwargs.setdefault("check", True)
    subprocess.run(cmd, *args, **kwargs)


class Workspace:
    def __init__(self):
        self.patch_dir = settings.ws_path / 'ws-patch'
        self.build_dir = settings.ws_path / '.build'
        self._bin_dir = settings.ws_path / '.bin'
        self._linker_dirs = {}
        self.builds = []

    @staticmethod
    def get_repository_prefixes():
        return settings.uri_schemes.value

    @staticmethod
    def get_default_linker():
        return settings.default_linker.value

    def find_build(self, build_name, before=None):
        i = 0

        while i < len(self.builds):
            if before and self.builds[i] == before:
                return None

            if self.builds[i].name == build_name:
                return self.builds[i]

            i += 1

        return None

    def initialize_builds(self):
        for build in self.builds:
            build.initialize(self)

    def setup(self):
        self.initialize_builds()

        for build in self.builds:
            build.setup(self)

    def add_to_env(self, env):
        self.initialize_builds()

        for build in self.builds:
            build.add_to_env(env, self)

    def build(self):
        self.initialize_builds()
        self.setup()

        for build in self.builds:
            build.build(self)

    def clean(self):
        self.initialize_builds()

        for build in self.builds:
            build.clean(self)

        if self._bin_dir.exists():
            shutil.rmtree(self._bin_dir)
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)

        mypycache_dir = settings.ws_path / ".mypy_cache"
        if mypycache_dir.exists():
            shutil.rmtree(mypycache_dir)

    @staticmethod
    def get_env():
        env = os.environ.copy()
        env["CCACHE_BASEDIR"] = str(settings.ws_path.resolve())
        return env

    def add_linker_to_env(self, linker: Linker, env):
        linker_dir = self.get_linker_dir(linker)
        util.env_prepend_path(env, "PATH", linker_dir.resolve())

    def get_linker_dir(self, linker: Linker):
        if not linker in self._linker_dirs:
            linker_name = linker.value
            main_linker_dir = self._bin_dir / "linkers"
            linker_dir = main_linker_dir / linker_name
            if not linker_dir.exists():
                linker_dir.mkdir(parents=True)
                if linker == Linker.LD:
                    ld_frontend = "ld"
                else:
                    ld_frontend = f"ld.{linker_name}"
                linker_path = shutil.which(ld_frontend)
                assert linker_path is not None, f"Didn't find linker {linker_name}"
                os.symlink(linker_path, linker_dir / "ld")
            self._linker_dirs[linker] = linker_dir
        return self._linker_dirs[linker]
