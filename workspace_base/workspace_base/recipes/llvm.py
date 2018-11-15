import os, sys

import psutil

from workspace_base.workspace import Workspace, _run
from workspace_base.util import j_from_num_threads
from . import Recipe

from pathlib import Path


class LLVM(Recipe):
    default_name = "llvm"

    def __init__(self, branch, profile,
                 repository_llvm="https://llvm.org/git/llvm",
                 repository_test_suite="https://llvm.org/git/test-suite",
                 repository_clang="https://llvm.org/git/clang",
                 name=default_name):
        super().__init__(name)
        self.branch = branch
        self.profile = profile
        self.repository_llvm = repository_llvm
        self.repository_test_suite = repository_test_suite
        self.repository_clang = repository_clang

    def _make_build_path(self, ws: Workspace):
        return ws.build_dir / self.name / self.profile

    def build(self, ws: Workspace):
        local_repo_path = ws.ws_path / self.name

        if not local_repo_path.is_dir():
            ws.reference_clone(
                self.repository_llvm,
                target_path=local_repo_path,
                branch=self.branch)
            ws.apply_patches("llvm", local_repo_path)

        test_suite_path = local_repo_path / 'projects/test-suite'
        if not test_suite_path.is_dir():
            ws.reference_clone(
                self.repository_test_suite,
                target_path=test_suite_path,
                branch=self.branch)
            ws.apply_patches("llvm-test-suite", test_suite_path)

        clang_path = local_repo_path / 'tools/clang'
        if not clang_path.is_dir():
            ws.reference_clone(
                self.repository_clang,
                target_path=clang_path,
                branch=self.branch)
            ws.apply_patches("clang", clang_path)

        build_path = self._make_build_path(ws)
        if not build_path.exists():
            os.makedirs(build_path)

            cmake_args = [
                '-G', 'Ninja', '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
                '-DLLVM_ENABLE_ASSERTIONS=On', '-DLLVM_TARGETS_TO_BUILD=X86',
                '-DCMAKE_CXX_FLAGS=-std=c++11 -fuse-ld=gold -fdiagnostics-color=always',
                '-DHAVE_VALGRIND_VALGRIND_H=0', local_repo_path
            ]

            if self.profile == "debug":
                cmake_args += ["-DCMAKE_BUILD_TYPE=Debug"]
                avail_mem =  psutil.virtual_memory().available
                if avail_mem < ws.args.num_threads * 12000000000:
                    print("[LLVM] less than 12G memory per thread available during a debug build; restricting link-parallelism to 1 [-DLLVM_PARALLEL_LINK_JOBS=1]")
                    cmake_args += ["-DLLVM_PARALLEL_LINK_JOBS=1"]
            elif self.profile == "release":
                cmake_args += ["-DCMAKE_BUILD_TYPE=Release"]
            else:
                raise RuntimeException(
                    f"[LLVM] unknown profile: '{self.profile}' (available: 'debug', 'release')")

            _run(["cmake"] + cmake_args, cwd=build_path)

        _run(["cmake", "--build", "."] + j_from_num_threads(ws.args.num_threads), cwd=build_path)

        self.build_output_path = build_path

    def add_to_env(self, env, ws: Workspace):
        env["PATH"] = str(self._make_build_path(ws) / "bin") + ":" + env["PATH"]
