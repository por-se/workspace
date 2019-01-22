import os, sys, shutil
from hashlib import blake2s

import psutil

from workspace.workspace import Workspace, _run
from workspace.util import j_from_num_threads, adjusted_cmake_args
from . import Recipe

from pathlib import Path


class LLVM(Recipe):
    default_name = "llvm"
    profiles = {
        "release": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Release',
                '-DLLVM_ENABLE_ASSERTIONS=On',
            ],
            "c_flags": "",
            "cxx_flags": "",
        },
        "rel+debinfo": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
                '-DLLVM_ENABLE_ASSERTIONS=On',
            ],
            "c_flags": "-fno-omit-frame-pointer",
            "cxx_flags": "-fno-omit-frame-pointer",
        },
        "debug": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Debug',
                '-DLLVM_ENABLE_ASSERTIONS=On',
            ],
            "c_flags": "",
            "cxx_flags": "",
        },
    }


    def __init__(self,
                 branch,
                 profile,
                 repository_llvm="https://github.com/llvm/llvm-project.git",
                 name=default_name,
                 cmake_adjustments=[]):
        """Build LLVM."""
        super().__init__(name)
        self.branch = branch
        self.profile = profile
        self.repository_llvm = repository_llvm
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
                self.repository_llvm,
                target_path=local_repo_path,
                branch=self.branch,
                sparse=["/llvm", "/clang"])
            ws.apply_patches("llvm", local_repo_path)

    def build(self, ws: Workspace):
        local_repo_path = self.paths.local_repo_path
        build_path = self.paths.build_path

        env = os.environ
        env["CCACHE_BASEDIR"] = str(ws.ws_path.resolve())

        if not build_path.exists():
            os.makedirs(build_path)

            cmake_args = [
                '-G', 'Ninja',
                '-DCMAKE_C_COMPILER_LAUNCHER=ccache',
                '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
                f'-DCMAKE_C_FLAGS=-fdiagnostics-color=always -fdebug-prefix-map={str(ws.ws_path.resolve())}=. {self.profiles[self.profile]["c_flags"]}',
                f'-DCMAKE_CXX_FLAGS=-fdiagnostics-color=always -fdebug-prefix-map={str(ws.ws_path.resolve())}=. -std=c++11 {self.profiles[self.profile]["cxx_flags"]}',
                '-DLLVM_USE_LINKER=gold',
                f'-DLLVM_EXTERNAL_CLANG_SOURCE_DIR={local_repo_path / "clang"}',
                '-DLLVM_TARGETS_TO_BUILD=X86',
                '-DLLVM_INCLUDE_EXAMPLES=Off',
                '-DHAVE_VALGRIND_VALGRIND_H=0',
            ]

            avail_mem = psutil.virtual_memory().available
            if self.profile != "release":
                if avail_mem < ws.args.num_threads * 12000000000 and avail_mem < 35000000000:
                    print(
                        "[{self.__class__.__name__}] less than 12G memory per thread (or 35G total) available during a build containing debug information; restricting link-parallelism to 1 [-DLLVM_PARALLEL_LINK_JOBS=1]"
                    )
                    cmake_args += ["-DLLVM_PARALLEL_LINK_JOBS=1"]

            cmake_args = cmake_args + self.profiles[self.profile]["cmake_args"]
            cmake_args = adjusted_cmake_args(cmake_args, self.cmake_adjustments)

            _run(["cmake"] + cmake_args + [local_repo_path / "llvm"], cwd=build_path, env=env)

        _run(["cmake", "--build", "."] + j_from_num_threads(ws.args.num_threads), cwd=build_path, env=env)

        self.build_output_path = build_path

    def clean(self, ws: Workspace):
        int_paths = self.paths
        if int_paths.build_path.is_dir():
            shutil.rmtree(int_paths.build_path)
        if ws.args.dist_clean:
            if int_paths.local_repo_path.is_dir():
                shutil.rmtree(int_paths.local_repo_path)
            ws.git_remove_exclude_path(int_paths.local_repo_path)

    def add_to_env(self, env, ws: Workspace):
        build_path = self.paths.build_path
        env["PATH"] = str(build_path / "bin") + ":" + env["PATH"]
