import os, sys, shutil

import psutil

from workspace_base.workspace import Workspace, _run
from workspace_base.util import j_from_num_threads
from . import Recipe

from pathlib import Path


class LLVM(Recipe):
    default_name = "llvm"

    def __init__(self,
                 branch,
                 profile,
                 repository_llvm="https://llvm.org/git/llvm",
                 repository_test_suite="https://llvm.org/git/test-suite",
                 repository_clang="https://llvm.org/git/clang",
                 name=default_name):
        """Build LLVM."""
        super().__init__(name)
        self.branch = branch
        self.profile = profile
        self.repository_llvm = repository_llvm
        self.repository_test_suite = repository_test_suite
        self.repository_clang = repository_clang

    def _make_internal_paths(self, ws: Workspace):
        class InternalPaths:
            pass

        res = InternalPaths()
        res.local_repo_path = ws.ws_path / self.name
        res.test_suite_path = res.local_repo_path / 'projects/test-suite'
        res.clang_path = res.local_repo_path / 'tools/clang'
        res.build_path = ws.build_dir / self.name

        return res

    def build(self, ws: Workspace):
        internal_paths = self._make_internal_paths(ws)

        local_repo_path = internal_paths.local_repo_path
        if not local_repo_path.is_dir():
            ws.reference_clone(
                self.repository_llvm,
                target_path=local_repo_path,
                branch=self.branch)
            ws.apply_patches("llvm", local_repo_path)

        test_suite_path = internal_paths.test_suite_path
        if not test_suite_path.is_dir():
            ws.reference_clone(
                self.repository_test_suite,
                target_path=test_suite_path,
                branch=self.branch)
            ws.apply_patches("llvm-test-suite", test_suite_path)

        clang_path = internal_paths.clang_path
        if not clang_path.is_dir():
            ws.reference_clone(
                self.repository_clang,
                target_path=clang_path,
                branch=self.branch)
            ws.apply_patches("clang", clang_path)

        build_path = internal_paths.build_path
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
                avail_mem = psutil.virtual_memory().available
                if avail_mem < ws.args.num_threads * 12000000000 and avail_mem < 35000000000:
                    print(
                        "[LLVM] less than 12G memory per thread (or 35G total) available during a debug build; restricting link-parallelism to 1 [-DLLVM_PARALLEL_LINK_JOBS=1]"
                    )
                    cmake_args += ["-DLLVM_PARALLEL_LINK_JOBS=1"]
            elif self.profile == "release":
                cmake_args += ["-DCMAKE_BUILD_TYPE=Release"]
            else:
                raise RuntimeException(
                    f"[LLVM] unknown profile: '{self.profile}' (available: 'debug', 'release')"
                )

            _run(["cmake"] + cmake_args, cwd=build_path)

        _run(
            ["cmake", "--build", "."] + j_from_num_threads(
                ws.args.num_threads),
            cwd=build_path)

        self.build_output_path = build_path

    def clean(self, ws: Workspace):
        ips = self._make_internal_paths(ws)
        shutil.rmtree(ips.build_path)
        if ws.args.dist_clean:
            shutil.rmtree(ips.local_repo_path)

    def add_to_env(self, env, ws: Workspace):
        build_path = self._make_internal_paths(ws).build_path
        env["PATH"] = str(build_path / "bin") + ":" + env["PATH"]
