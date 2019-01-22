import os, shutil
from hashlib import blake2s

from workspace.workspace import Workspace, _run
from workspace.util import j_from_num_threads, adjusted_cmake_args
from . import Recipe

from pathlib import Path


class SIMULATOR(Recipe):
    default_name = "simulator"
    profiles = {
        "release": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Release',
            ],
            "cxx_flags": "",
        },
        "rel+debinfo": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
            ],
            "cxx_flags": "-fno-omit-frame-pointer",
        },
        "debug": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Debug',
            ],
            "cxx_flags": "",
        },
        "sanitized": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Asan',
            ],
            "cxx_flags": "",
        },
    }

    def __init__(self,
                 branch,
                 profile,
                 repository="git@laboratory.comsys.rwth-aachen.de:concurrent-symbolic-execution/simulator.git",
                 name=default_name,
                 cmake_adjustments=[]):
        super().__init__(name)
        self.branch = branch
        self.profile = profile
        self.repository = repository
        self.cmake_adjustments = cmake_adjustments

        assert self.profile in self.profiles, f'[{self.__class__.__name__}] the recipe for {self.name} does not contain a profile "{self.profile}"!'

    def initialize(self, ws: Workspace):
        def _compute_digest(self, ws: Workspace):
            digest = blake2s()
            digest.update(self.name.encode())
            digest.update(self.profile.encode())
            for adjustment in self.cmake_adjustments:
                digest.update("CMAKE_ADJUSTMENT:".encode())
                digest.update(adjustment.encode())

            # branch and repository need not be part of the digest, as we will build whatever
            # we find at the target path, no matter what it turns out to be at build time

            return digest.hexdigest()[:12]

        def _make_internal_paths(self, ws: Workspace):
            class InternalPaths:
                pass

            res = InternalPaths()
            res.local_repo_path = ws.ws_path / self.name
            res.build_path = ws.build_dir / f'{self.name}-{self.profile}-{self.digest}'
            return res

        self.digest = _compute_digest(self, ws)
        self.paths = _make_internal_paths(self, ws)

    def setup(self, ws: Workspace):
        local_repo_path = self.paths.local_repo_path
        if not local_repo_path.is_dir():
            ws.git_add_exclude_path(local_repo_path)
            ws.reference_clone(
                self.repository,
                target_path=local_repo_path,
                branch=self.branch)
            ws.apply_patches("simulator", local_repo_path)

    def build(self, ws: Workspace):
        local_repo_path = self.paths.local_repo_path
        build_path = self.paths.build_path

        env = os.environ
        env["CCACHE_BASEDIR"] = str(ws.ws_path.resolve())

        if not build_path.exists():
            os.makedirs(build_path)

            cmake_args = [
                '-G', 'Ninja',
                '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
                f'-DCMAKE_CXX_FLAGS=-fuse-ld=gold -fdiagnostics-color=always -fdebug-prefix-map={str(ws.ws_path.resolve())}=. {self.profiles[self.profile]["cxx_flags"]}',
            ]

            cmake_args = cmake_args + self.profiles[self.profile]["cmake_args"]
            cmake_args = adjusted_cmake_args(cmake_args, self.cmake_adjustments)

            _run(["cmake"] + cmake_args + [local_repo_path], cwd=build_path, env=env)

        _run(["cmake", "--build", "."] + j_from_num_threads(ws.args.num_threads), cwd=build_path, env=env)

        self.build_output_path = build_path
        self.repo_path = local_repo_path

    def clean(self, ws: Workspace):
        int_paths = self.paths
        if int_paths.build_path.is_dir():
            shutil.rmtree(int_paths.build_path)
        if ws.args.dist_clean:
            if int_paths.local_repo_path.is_dir():
                shutil.rmtree(int_paths.local_repo_path)
            ws.git_remove_exclude_path(int_paths.local_repo_path)

    def add_to_env(self, env, ws: Workspace):
        Recipe._env_prepend_path(env, "PATH", self.paths.build_path / "bin/random-graph")
