import os, shutil
from hashlib import blake2s

from workspace.workspace import Workspace, _run
from workspace.util import j_from_num_threads
from . import Recipe, MINISAT

from pathlib import Path


class STP(Recipe):
    default_name = "stp"
    profiles = {
        "release": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Release',
                '-DENABLE_ASSERTIONS=On',
                '-DSANITIZE=Off',
            ],
            "c_flags": "",
            "cxx_flags": "",
        },
        "rel+debinfo": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
                '-DENABLE_ASSERTIONS=On',
                '-DSANITIZE=Off',
            ],
            "c_flags": "-fno-omit-frame-pointer",
            "cxx_flags": "-fno-omit-frame-pointer",
        },
        "debug": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Debug',
                '-DENABLE_ASSERTIONS=On',
                '-DSANITIZE=Off',
            ],
            "c_flags": "",
            "cxx_flags": "",
        },
    }

    def __init__(self,
                 branch,
                 profile,
                 name=default_name,
                 repository="git@github.com:stp/stp.git",
                 minisat_name=MINISAT.default_name,
                 cmake_adjustments=[]):
        super().__init__(name)
        self.branch = branch
        self.profile = profile
        self.repository = repository
        self.minisat_name = minisat_name
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

            minisat = ws.find_build(build_name=self.minisat_name, before=self)
            assert minisat, "STP requires minisat"
            digest.update(minisat.digest.encode())

            return digest.hexdigest()[:12]

        def _make_internal_paths(self, ws: Workspace):
            class InternalPaths:
                pass

            res = InternalPaths()
            res.src_dir = ws.ws_path / self.name
            res.build_dir = ws.build_dir / f'{self.name}-{self.profile}-{self.digest}'
            return res

        self.digest = _compute_digest(self, ws)
        self.paths = _make_internal_paths(self, ws)

    def setup(self, ws: Workspace):
        src_dir = self.paths.src_dir
        if not src_dir.is_dir():
            ws.git_add_exclude_path(src_dir)
            ws.reference_clone(
                self.repository,
                target_path=src_dir,
                branch=self.branch)
            ws.apply_patches("stp", src_dir)

    def build(self, ws: Workspace):
        env = os.environ
        env["CCACHE_BASEDIR"] = str(ws.ws_path.resolve())

        if not self.paths.build_dir.exists():
            os.makedirs(self.paths.build_dir)

            minisat = ws.find_build(build_name=self.minisat_name, before=self)

            assert minisat, "STP requires minisat"

            cmake_args = [
                '-G', 'Ninja',
                '-DCMAKE_C_COMPILER_LAUNCHER=ccache',
                '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
                f'-DCMAKE_C_FLAGS=-fuse-ld=gold -fdiagnostics-color=always -fdebug-prefix-map={str(ws.ws_path.resolve())}=. {self.profiles[self.profile]["c_flags"]}',
                f'-DCMAKE_CXX_FLAGS=-fuse-ld=gold -fdiagnostics-color=always -fdebug-prefix-map={str(ws.ws_path.resolve())}=. -std=c++11 {self.profiles[self.profile]["cxx_flags"]}',
                f'-DMINISAT_LIBRARY={minisat.paths.build_dir}/libminisat.a',
                f'-DMINISAT_INCLUDE_DIR={minisat.paths.src_dir}',
                '-DNOCRYPTOMINISAT=On',
                '-DSTATICCOMPILE=On',
                '-DBUILD_SHARED_LIBS=Off',
                '-DENABLE_PYTHON_INTERFACE=Off',
            ]

            cmake_args = cmake_args + self.profiles[self.profile]["cmake_args"]
            cmake_args = Recipe.adjusted_cmake_args(cmake_args, self.cmake_adjustments)

            _run(["cmake"] + cmake_args + [self.paths.src_dir], cwd=self.paths.build_dir, env=env)

        _run(["cmake", "--build", "."] + j_from_num_threads(ws.args.num_threads), cwd=self.paths.build_dir, env=env)

    def clean(self, ws: Workspace):
        int_paths = self.paths
        if self.paths.build_dir.is_dir():
            shutil.rmtree(self.paths.build_dir)
        if ws.args.dist_clean:
            if self.paths.src_dir.is_dir():
                shutil.rmtree(self.paths.src_dir)
            ws.git_remove_exclude_path(self.paths.src_dir)
