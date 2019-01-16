import os, multiprocessing, shutil
from hashlib import blake2s

from workspace.workspace import Workspace, _run
from workspace.util import j_from_num_threads, adjusted_cmake_args
from . import Recipe, STP, Z3, LLVM, KLEE_UCLIBC

from pathlib import Path


class KLEE(Recipe):
    default_name = "klee"
    profiles = {
        "release": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Release',
                '-DKLEE_RUNTIME_BUILD_TYPE=Release',
            ],
            "c_flags": "",
            "cxx_flags": "",
        },
        "debug": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Debug',
                '-DKLEE_RUNTIME_BUILD_TYPE=Debug',
            ],
            "c_flags": "",
            "cxx_flags": "",
        },
        "sanitized": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Release',
                '-DKLEE_RUNTIME_BUILD_TYPE=Debug',
            ],
            "c_flags": "",
            "cxx_flags": "",
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
        if not profile in self.profiles:
            raise RuntimeError

        super().__init__(name)
        self.branch = branch
        self.profile = profile
        self.repository = repository
        self.stp_name = stp_name
        self.z3_name = z3_name
        self.llvm_name = llvm_name
        self.klee_uclibc_name = klee_uclibc_name
        self.cmake_adjustments = cmake_adjustments

    def _compute_digest(self, ws: Workspace):
        if self.digest is None:
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

            self.digest = digest.hexdigest()[:12]
        return self.digest

    def _make_internal_paths(self, ws: Workspace):
        class InternalPaths:
            pass

        res = InternalPaths()
        res.local_repo_path = ws.ws_path / self.name
        res.build_path = ws.build_dir / f'{self.name}-{self.profile}-{self._compute_digest(ws)}'
        return res

    def build(self, ws: Workspace):
        int_paths = self._make_internal_paths(ws)
        self._compute_digest(ws)

        local_repo_path = int_paths.local_repo_path
        if not local_repo_path.is_dir():
            ws.reference_clone(
                self.repository,
                target_path=local_repo_path,
                branch=self.branch)
            ws.apply_patches("klee", local_repo_path)

        build_path = int_paths.build_path

        env = os.environ
        env["CCACHE_BASEDIR"] = str(ws.ws_path.resolve())

        if not build_path.exists():
            os.makedirs(build_path)

            stp = ws.find_build(build_name=self.stp_name, before=self)
            z3 = ws.find_build(build_name=self.z3_name, before=self)
            llvm = ws.find_build(build_name=self.llvm_name, before=self)
            klee_uclibc = ws.find_build(
                build_name=self.klee_uclibc_name, before=self)

            assert stp, "klee requires stp"
            assert z3, "klee requires z3"
            assert llvm, "klee requires llvm"
            assert klee_uclibc, "klee requires klee_uclibc"

            cmake_args = [
                '-G', 'Ninja',
                '-DCMAKE_C_COMPILER_LAUNCHER=ccache',
                '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
                f'-DCMAKE_C_FLAGS=-fuse-ld=gold -fdiagnostics-color=always -fdebug-prefix-map={str(ws.ws_path.resolve())}=. {self.profiles[self.profile]["c_flags"]}',
                f'-DCMAKE_CXX_FLAGS=-fuse-ld=gold -fdiagnostics-color=always -fdebug-prefix-map={str(ws.ws_path.resolve())}=. -fno-rtti {self.profiles[self.profile]["cxx_flags"]}',
                '-DUSE_CMAKE_FIND_PACKAGE_LLVM=On',
                f'-DLLVM_DIR={llvm.build_output_path}/lib/cmake/llvm/',
                '-DENABLE_SOLVER_STP=On',
                f'-DSTP_DIR={stp.stp_dir}',
                f'-DSTP_STATIC_LIBRARY={stp.build_output_path}/lib/libstp.a',
                '-DENABLE_SOLVER_Z3=On',
                f'-DZ3_INCLUDE_DIRS={z3.z3_dir}/src/api/',
                f'-DZ3_LIBRARIES={z3.build_output_path}/libz3.a',
                '-DENABLE_POSIX_RUNTIME=On',
                '-DENABLE_KLEE_UCLIBC=On',
                f'-DKLEE_UCLIBC_PATH={klee_uclibc.repo_path}',
                f'-DLIT_TOOL={shutil.which("lit")}',
                '-DENABLE_SYSTEM_TESTS=On',
                # Waiting for this to be merged:
                # https://github.com/klee/klee/pull/1005
                '-DENABLE_UNIT_TESTS=Off',
                '-DENABLE_TCMALLOC=On',
            ]

            cmake_args = cmake_args + self.profiles[self.profile]["cmake_args"]
            cmake_args = adjusted_cmake_args(cmake_args, self.cmake_adjustments)

            _run(
                ["cmake"] + cmake_args + [local_repo_path],
                cwd=build_path, env=env)

        _run(["cmake", "--build", "."] + j_from_num_threads(ws.args.num_threads), cwd=build_path, env=env)

    def clean(self, ws: Workspace):
        int_paths = self._make_internal_paths(ws)
        if int_paths.build_path.is_dir():
            shutil.rmtree(int_paths.build_path)
        if ws.args.dist_clean and int_paths.local_repo_path.is_dir():
            shutil.rmtree(int_paths.local_repo_path)

    def add_to_env(self, env, ws: Workspace):
        build_path = self._make_internal_paths(ws).build_path
        env["PATH"] = str(build_path / "bin") + ":" + env["PATH"]
