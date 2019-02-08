import os, shutil, psutil
from hashlib import blake2s

from workspace.workspace import Workspace, _run
from workspace.util import j_from_num_threads, env_prepend_path
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
                 repository="https://github.com/llvm/llvm-project.git",
                 name=default_name,
                 cmake_adjustments=[]):
        """Build LLVM."""
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
            paths.tablegen = paths.build_dir / 'bin/llvm-tblgen'
            return paths

        if self.profile != "release":
            self._release_build = LLVM(self.branch, "release", self.repository, self.name, [])
            self._release_build.initialize(ws)

        self.digest = _compute_digest(self, ws)
        self.paths = _make_internal_paths(self, ws)

    def setup(self, ws: Workspace):
        if self.profile != "release":
            self._release_build.setup(ws)

        if not self.paths.src_dir.is_dir():
            ws.git_add_exclude_path(self.paths.src_dir)
            ws.reference_clone(
                self.repository,
                target_path=self.paths.src_dir,
                branch=self.branch,
                sparse=["/llvm", "/clang"])
            ws.apply_patches("llvm", self.paths.src_dir)

    def build(self, ws: Workspace, target=None):
        if self.profile != "release":
            self._release_build.build(ws, target='bin/llvm-tblgen')

        env = ws.get_env()

        if not self.paths.build_dir.exists():
            os.makedirs(self.paths.build_dir)

            cmake_args = [
                '-G', 'Ninja',
                '-DCMAKE_C_COMPILER_LAUNCHER=ccache',
                '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
                f'-DCMAKE_C_FLAGS=-fdiagnostics-color=always -fdebug-prefix-map={str(ws.ws_path.resolve())}=. {self.profiles[self.profile]["c_flags"]}',
                f'-DCMAKE_CXX_FLAGS=-fdiagnostics-color=always -fdebug-prefix-map={str(ws.ws_path.resolve())}=. -std=c++11 {self.profiles[self.profile]["cxx_flags"]}',
                f'-DCMAKE_MODULE_LINKER_FLAGS=-Xlinker --no-threads',
                f'-DCMAKE_SHARED_LINKER_FLAGS=-Xlinker --no-threads',
                f'-DCMAKE_EXE_LINKER_FLAGS=-Xlinker --no-threads -Xlinker --gdb-index',
                f'-DLLVM_EXTERNAL_CLANG_SOURCE_DIR={self.paths.src_dir / "clang"}',
                '-DLLVM_TARGETS_TO_BUILD=X86',
                '-DLLVM_INCLUDE_EXAMPLES=Off',
                '-DHAVE_VALGRIND_VALGRIND_H=0',
            ]
            if self.profile != "release":
                cmake_args += [f'-DLLVM_TABLEGEN={self._release_build.paths.tablegen}']

            avail_mem = psutil.virtual_memory().available
            if self.profile != "release" and  avail_mem < ws.args.num_threads * 12000000000 and avail_mem < 35000000000:
                print(
                    "[{self.__class__.__name__}] less than 12G memory per thread (or 35G total) available during a build containing debug information; restricting link-parallelism to 1 [-DLLVM_PARALLEL_LINK_JOBS=1]"
                )
                cmake_args += ["-DLLVM_PARALLEL_LINK_JOBS=1"]

            cmake_args = cmake_args + self.profiles[self.profile]["cmake_args"]
            cmake_args = Recipe.adjusted_cmake_args(cmake_args, self.cmake_adjustments)

            _run(["cmake"] + cmake_args + [self.paths.src_dir / "llvm"], cwd=self.paths.build_dir, env=env)

        build_call = ["cmake", "--build", "."] + j_from_num_threads(ws.args.num_threads)
        if target is not None:
            build_call += ['--target', target]
        _run(build_call, cwd=self.paths.build_dir, env=env)

    def clean(self, ws: Workspace):
        if self.paths.build_dir.is_dir():
            shutil.rmtree(self.paths.build_dir)
        if ws.args.dist_clean:
            if self.paths.src_dir.is_dir():
                shutil.rmtree(self.paths.src_dir)
            ws.git_remove_exclude_path(self.paths.src_dir)

    def add_to_env(self, env, ws: Workspace):
        env_prepend_path(env, "PATH", self.paths.build_dir / "bin")
