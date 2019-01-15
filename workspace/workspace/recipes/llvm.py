import os, sys, shutil
from hashlib import blake2s

import psutil

from workspace.workspace import Workspace, _run
from workspace.util import j_from_num_threads, adjusted_cmake_args
from . import Recipe

from pathlib import Path


class LLVM(Recipe):
    default_name = "llvm"

    def __init__(self,
                 branch,
                 profile,
                 repository_llvm="https://github.com/llvm/llvm-project.git",
                 repository_test_suite="https://github.com/llvm/llvm-test-suite.git",
                 name=default_name,
                 cmake_adjustments=[]):
        """Build LLVM."""
        super().__init__(name)
        self.branch = branch
        self.profile = profile
        self.repository_llvm = repository_llvm
        self.repository_test_suite = repository_test_suite
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

            self.digest = digest.hexdigest()[:12]
        return self.digest

    def _make_internal_paths(self, ws: Workspace):
        class InternalPaths:
            pass

        res = InternalPaths()
        res.local_repo_path = ws.ws_path / self.name
        res.test_suite_path = res.local_repo_path / 'projects/test-suite'
        res.build_path = ws.build_dir / f'{self.name}-{self.profile}-{self._compute_digest(ws)}'
        return res

    def build(self, ws: Workspace):
        internal_paths = self._make_internal_paths(ws)
        self._compute_digest(ws)

        local_repo_path = internal_paths.local_repo_path
        if not local_repo_path.is_dir():
            ws.reference_clone(
                self.repository_llvm,
                target_path=local_repo_path,
                branch=self.branch,
                sparse=["/llvm", "/clang"])
            ws.apply_patches("llvm", local_repo_path)
            os.symlink(local_repo_path / "clang", local_repo_path / "llvm/tools/clang")

        test_suite_path = internal_paths.test_suite_path
        if not test_suite_path.is_dir():
            ws.reference_clone(
                self.repository_test_suite,
                target_path=test_suite_path,
                branch=self.branch)
            ws.apply_patches("llvm-test-suite", test_suite_path)

        build_path = internal_paths.build_path
        if not build_path.exists():
            os.makedirs(build_path)

            cmake_args = [
                '-G', 'Ninja', '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
                '-DLLVM_ENABLE_ASSERTIONS=On', '-DLLVM_TARGETS_TO_BUILD=X86',
                '-DCMAKE_CXX_FLAGS=-std=c++11 -fuse-ld=gold -fdiagnostics-color=always',
                '-DHAVE_VALGRIND_VALGRIND_H=0',
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

            cmake_args = adjusted_cmake_args(cmake_args, self.cmake_adjustments)

            _run(["cmake"] + cmake_args + [local_repo_path / "llvm"], cwd=build_path)

        _run(["cmake", "--build", "."] + j_from_num_threads(ws.args.num_threads), cwd=build_path)

        self.build_output_path = build_path

    def clean(self, ws: Workspace):
        int_paths = self._make_internal_paths(ws)
        if int_paths.build_path.is_dir():
            shutil.rmtree(int_paths.build_path)
        if ws.args.dist_clean and int_paths.local_repo_path.is_dir():
            shutil.rmtree(int_paths.local_repo_path)

    def add_to_env(self, env, ws: Workspace):
        build_path = self._make_internal_paths(ws).build_path
        env["PATH"] = str(build_path / "bin") + ":" + env["PATH"]
