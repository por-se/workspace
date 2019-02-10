import os, shutil
from hashlib import blake2s

from workspace.workspace import Workspace, _run
from workspace.util import j_from_num_threads, env_prepend_path
from . import Recipe, STP, Z3, LLVM, KLEE_UCLIBC

from pathlib import Path


class KLEE(Recipe):
    default_name = "klee"
    profiles = {
        "release": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Release',
                '-DKLEE_RUNTIME_BUILD_TYPE=Release',
                '-DENABLE_TCMALLOC=On',
            ],
            "c_flags": "",
            "cxx_flags": "",
        },
        "rel+debinfo": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
                '-DKLEE_RUNTIME_BUILD_TYPE=Release',
                '-DENABLE_TCMALLOC=On',
            ],
            "c_flags": "-fno-omit-frame-pointer",
            "cxx_flags": "-fno-omit-frame-pointer",
        },
        "debug": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Debug',
                '-DKLEE_RUNTIME_BUILD_TYPE=Debug',
                '-DENABLE_TCMALLOC=On',
            ],
            "c_flags": "",
            "cxx_flags": "",
        },
        "sanitized": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Debug',
                '-DKLEE_RUNTIME_BUILD_TYPE=Release',
                '-DENABLE_TCMALLOC=Off',
            ],
            "c_flags": "-fsanitize=address -fsanitize=undefined",
            "cxx_flags": "-fsanitize=address -fsanitize=undefined",
        },
    }

    def __init__(self,
                 branch,
                 profile,
                 name=default_name,
                 repository="git@github.com:klee/klee.git",
                 stp_name=STP.default_name,
                 z3_name=Z3.default_name,
                 llvm_name=LLVM.default_name,
                 klee_uclibc_name=KLEE_UCLIBC.default_name,
                 cmake_adjustments=[]):

        super().__init__(name)
        self.branch = branch
        self.profile = profile
        self.repository = repository
        self.stp_name = stp_name
        self.z3_name = z3_name
        self.llvm_name = llvm_name
        self.klee_uclibc_name = klee_uclibc_name
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

            stp = ws.find_build(build_name=self.stp_name, before=self)
            z3 = ws.find_build(build_name=self.z3_name, before=self)
            llvm = ws.find_build(build_name=self.llvm_name, before=self)
            klee_uclibc = ws.find_build(
                build_name=self.klee_uclibc_name, before=self)

            assert stp, "klee requires stp"
            assert z3, "klee requires z3"
            assert llvm, "klee requires llvm"
            assert klee_uclibc, "klee requires klee_uclibc"

            digest.update(stp.digest.encode())
            digest.update(z3.digest.encode())
            digest.update(llvm.digest.encode())
            digest.update(klee_uclibc.digest.encode())

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
            ws.apply_patches("klee", self.paths.src_dir)

    def build(self, ws: Workspace):
        env = ws.get_env()

        if not self.paths.build_dir.exists():
            os.makedirs(self.paths.build_dir)

            stp = ws.find_build(build_name=self.stp_name, before=self)
            z3 = ws.find_build(build_name=self.z3_name, before=self)
            llvm = ws.find_build(build_name=self.llvm_name, before=self)
            klee_uclibc = ws.find_build(build_name=self.klee_uclibc_name, before=self)

            assert stp, "klee requires stp"
            assert z3, "klee requires z3"
            assert llvm, "klee requires llvm"
            assert klee_uclibc, "klee requires klee_uclibc"

            cmake_args = [
                '-G', 'Ninja',
                '-DCMAKE_C_COMPILER_LAUNCHER=ccache',
                '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
                f'-DCMAKE_C_FLAGS=-fdiagnostics-color=always -fdebug-prefix-map={str(ws.ws_path.resolve())}=. {self.profiles[self.profile]["c_flags"]}',
                f'-DCMAKE_CXX_FLAGS=-fdiagnostics-color=always -fdebug-prefix-map={str(ws.ws_path.resolve())}=. -fno-rtti {self.profiles[self.profile]["cxx_flags"]}',
                f'-DCMAKE_STATIC_LINKER_FLAGS=-T',
                f'-DCMAKE_MODULE_LINKER_FLAGS=-Xlinker --no-threads',
                f'-DCMAKE_SHARED_LINKER_FLAGS=-Xlinker --no-threads',
                f'-DCMAKE_EXE_LINKER_FLAGS=-Xlinker --no-threads -Xlinker --gdb-index',
                '-DUSE_CMAKE_FIND_PACKAGE_LLVM=On',
                f'-DLLVM_DIR={llvm.paths.build_dir}/lib/cmake/llvm/',
                '-DENABLE_SOLVER_STP=On',
                f'-DSTP_DIR={stp.paths.src_dir}',
                f'-DSTP_STATIC_LIBRARY={stp.paths.build_dir}/lib/libstp.a',
                '-DENABLE_SOLVER_Z3=On',
                f'-DZ3_INCLUDE_DIRS={z3.paths.src_dir}/src/api/',
                f'-DZ3_LIBRARIES={z3.paths.build_dir}/libz3.a',
                '-DENABLE_POSIX_RUNTIME=On',
                '-DENABLE_KLEE_UCLIBC=On',
                f'-DKLEE_UCLIBC_PATH={klee_uclibc.paths.build_dir}',
                f'-DLIT_TOOL={shutil.which("lit")}',
                '-DENABLE_SYSTEM_TESTS=On',
                # Waiting for this to be merged:
                # https://github.com/klee/klee/pull/1005
                '-DENABLE_UNIT_TESTS=Off',
            ]

            cmake_args = cmake_args + self.profiles[self.profile]["cmake_args"]
            cmake_args = Recipe.adjusted_cmake_args(cmake_args, self.cmake_adjustments)

            _run(["cmake"] + cmake_args + [self.paths.src_dir], cwd=self.paths.build_dir, env=env)

        _run(["cmake", "--build", "."] + j_from_num_threads(ws.args.num_threads), cwd=self.paths.build_dir, env=env)

    def clean(self, ws: Workspace):
        if self.paths.build_dir.is_dir():
            shutil.rmtree(self.paths.build_dir)
        if ws.args.dist_clean:
            if self.paths.src_dir.is_dir():
                shutil.rmtree(self.paths.src_dir)
            ws.git_remove_exclude_path(self.paths.src_dir)

    def add_to_env(self, env, ws: Workspace):
        env_prepend_path(env, "PATH", self.paths.build_dir / "bin")
        env_prepend_path(env, "C_INCLUDE_PATH", self.paths.src_dir / "include")
