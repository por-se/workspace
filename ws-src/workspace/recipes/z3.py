import os, shutil
from hashlib import blake2s

from workspace.workspace import Workspace, _run
from workspace.util import j_from_num_threads, env_prepend_path
from . import Recipe

from pathlib import Path


class Z3(Recipe):
    default_name = "z3"
    profiles = {
        "release": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Release',
            ],
            "c_flags": "",
            "cxx_flags": "",
        },
        "rel+debinfo": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
            ],
            "c_flags": "-fno-omit-frame-pointer",
            "cxx_flags": "-fno-omit-frame-pointer",
        },
        "debug": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Debug',
            ],
            "c_flags": "",
            "cxx_flags": "",
        },
    }

    def __init__(self,
                 branch,
                 profile,
                 repository="git@github.com:Z3Prover/z3.git",
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

            paths = InternalPaths()
            paths.src_dir = ws.ws_path / self.name
            paths.build_dir = ws.build_dir / f'{self.name}-{self.profile}-{self.digest}'
            return paths

        self.digest = _compute_digest(self, ws)
        self.paths = _make_internal_paths(self, ws)

    def setup(self, ws: Workspace):
        if not self.paths.src_dir.is_dir():
            ws.git_add_exclude_path(self.paths.src_dir)
            ws.reference_clone(
                self.repository,
                target_path=self.paths.src_dir,
                branch=self.branch)
            ws.apply_patches("z3", self.paths.src_dir)

    def build(self, ws: Workspace):
        env = ws.get_env()

        if not self.paths.build_dir.exists():
            os.makedirs(self.paths.build_dir)

            cmake_args = [
                '-G', 'Ninja',
                '-DCMAKE_C_COMPILER_LAUNCHER=ccache',
                '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
                f'-DCMAKE_C_FLAGS=-fdiagnostics-color=always -fdebug-prefix-map={str(ws.ws_path.resolve())}=. {self.profiles[self.profile]["c_flags"]}',
                f'-DCMAKE_CXX_FLAGS=-fdiagnostics-color=always -fdebug-prefix-map={str(ws.ws_path.resolve())}=. {self.profiles[self.profile]["cxx_flags"]}',
                f'-DCMAKE_STATIC_LINKER_FLAGS=-T',
                f'-DCMAKE_MODULE_LINKER_FLAGS=-Xlinker --no-threads',
                f'-DCMAKE_SHARED_LINKER_FLAGS=-Xlinker --no-threads',
                f'-DCMAKE_EXE_LINKER_FLAGS=-Xlinker --no-threads -Xlinker --gdb-index',
                '-DBUILD_LIBZ3_SHARED=false',
                '-DUSE_OPENMP=0',
            ]

            cmake_args = Recipe.adjusted_cmake_args(cmake_args, self.profiles[self.profile]["cmake_args"])
            cmake_args = Recipe.adjusted_cmake_args(cmake_args, self.cmake_adjustments)

            _run(["cmake"] + cmake_args + [self.paths.src_dir], cwd=self.paths.build_dir, env=env)

        _run(["cmake", "--build", "."] + j_from_num_threads(ws.args.num_threads), cwd=self.paths.build_dir, env=env)

    def clean(self, ws: Workspace):
        if ws.args.dist_clean:
            if self.paths.src_dir.is_dir():
                shutil.rmtree(self.paths.src_dir)
            ws.git_remove_exclude_path(self.paths.src_dir)
