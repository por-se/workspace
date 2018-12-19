import os, multiprocessing, shutil

from workspace_base.workspace import Workspace, _run
from workspace_base.util import j_from_num_threads
from . import Recipe, STP, Z3, LLVM, KLEE_UCLIBC

from pathlib import Path


class KLEE(Recipe):
    default_name = "klee"
    profiles = {
        "release": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Release',
                '-DKLEE_RUNTIME_BUILD_TYPE=Release',
            ]
        },
        "debug": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Debug',
                '-DKLEE_RUNTIME_BUILD_TYPE=Debug',
            ]
        },
        "sanitized": {
            "cmake_args": [
                '-DCMAKE_BUILD_TYPE=Release',
                '-DKLEE_RUNTIME_BUILD_TYPE=Debug',
            ]
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
                 klee_uclibc_name=KLEE_UCLIBC.default_name):
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

    def _make_build_path(self, ws: Workspace):
        return ws.build_dir / self.name / self.profile

    def build(self, ws: Workspace):
        local_repo_path = ws.ws_path / self.name

        if not local_repo_path.is_dir():
            ws.reference_clone(
                self.repository,
                target_path=local_repo_path,
                branch=self.branch)
            ws.apply_patches("klee", local_repo_path)

        build_path = self._make_build_path(ws)
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
                '-G',
                'Ninja',
                '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
                '-DUSE_CMAKE_FIND_PACKAGE_LLVM=On',
                f'-DLLVM_DIR={llvm.build_output_path}/lib/cmake/llvm/',
                '-DENABLE_SOLVER_STP=On',
                f'-DSTP_DIR={stp.stp_dir}',
                f'-DSTP_STATIC_LIBRARY={stp.build_output_path}/lib/libstp.a',
                '-DENABLE_SOLVER_Z3=On',
                f'-DZ3_INCLUDE_DIRS={z3.z3_dir}/src/api/',
                f'-DZ3_LIBRARIES={z3.build_output_path}/libz3.a',
                '-DENABLE_PTHREAD_RUNTIME=On',
                '-DENABLE_POSIX_RUNTIME=On',
                '-DENABLE_KLEE_UCLIBC=On',
                f'-DKLEE_UCLIBC_PATH={klee_uclibc.repo_path}',
                f'-DLIT_TOOL={shutil.which("lit")}',
                '-DENABLE_SYSTEM_TESTS=On',
                # Waiting for this to be merged:
                # https://github.com/klee/klee/pull/1005
                '-DENABLE_UNIT_TESTS=Off',
                '-DENABLE_TCMALLOC=On',
                '-DCMAKE_CXX_FLAGS=-fno-rtti -fuse-ld=gold -fdiagnostics-color=always',
                local_repo_path
            ]

            _run(
                ["cmake"] + cmake_args +
                self.profiles[self.profile]["cmake_args"],
                cwd=build_path)

        _run(["cmake", "--build", "."] + j_from_num_threads(ws.args.num_threads), cwd=build_path)

    def add_to_env(self, env, ws: Workspace):
        env["PATH"] = str(self._make_build_path(ws) / "bin") + ":" + env["PATH"]