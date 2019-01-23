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
            ws.apply_patches("stp", local_repo_path)

    def build(self, ws: Workspace):
        local_repo_path = self.paths.local_repo_path
        build_path = self.paths.build_path

        env = os.environ
        env["CCACHE_BASEDIR"] = str(ws.ws_path.resolve())

        if not build_path.exists():
            os.makedirs(build_path)

            minisat = ws.find_build(build_name=self.minisat_name, before=self)

            assert minisat, "STP requires minisat"

            cmake_args = [
                '-G', 'Ninja',
                '-DCMAKE_C_COMPILER_LAUNCHER=ccache',
                '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
                f'-DCMAKE_C_FLAGS=-fuse-ld=gold -fdiagnostics-color=always -fdebug-prefix-map={str(ws.ws_path.resolve())}=. {self.profiles[self.profile]["c_flags"]}',
                f'-DCMAKE_CXX_FLAGS=-fuse-ld=gold -fdiagnostics-color=always -fdebug-prefix-map={str(ws.ws_path.resolve())}=. -std=c++11 {self.profiles[self.profile]["cxx_flags"]}',
                f'-DMINISAT_LIBRARY={minisat.build_output_path}/libminisat.a',
                f'-DMINISAT_INCLUDE_DIR={minisat.include_path}',
                '-DNOCRYPTOMINISAT=On',
                '-DSTATICCOMPILE=On',
                '-DBUILD_SHARED_LIBS=Off',
                '-DENABLE_PYTHON_INTERFACE=Off',
            ]

            cmake_args = cmake_args + self.profiles[self.profile]["cmake_args"]
            cmake_args = Recipe.adjusted_cmake_args(cmake_args, self.cmake_adjustments)

            _run(["cmake"] + cmake_args + [local_repo_path], cwd=build_path, env=env)

        _run(["cmake", "--build", "."] + j_from_num_threads(ws.args.num_threads), cwd=build_path, env=env)

        self.build_output_path = build_path
        self.stp_dir = local_repo_path

    def clean(self, ws: Workspace):
        int_paths = self.paths
        if int_paths.build_path.is_dir():
            shutil.rmtree(int_paths.build_path)
        if ws.args.dist_clean:
            if int_paths.local_repo_path.is_dir():
                shutil.rmtree(int_paths.local_repo_path)
            ws.git_remove_exclude_path(int_paths.local_repo_path)
