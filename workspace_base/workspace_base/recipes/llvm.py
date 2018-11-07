import os

from workspace_base.workspace import Workspace, _run
from . import Recipe

from pathlib import Path


class LLVM(Recipe):
    def __init__(self, branch, profile, name="llvm"):
        super().__init__(name)
        self.branch = branch
        self.profile = profile

    def build(self, ws: Workspace):
        local_repo_path = ws.ws_path / self.name

        if not local_repo_path.is_dir():
            ws.reference_clone(
                "https://llvm.org/git/llvm",
                target_path=local_repo_path,
                branch=self.branch)
            ws.apply_patches("llvm", local_repo_path)

        test_suite_path = local_repo_path / 'projects/test-suite'
        if not test_suite_path.is_dir():
            ws.reference_clone(
                "https://llvm.org/git/llvm",
                target_path=test_suite_path,
                branch=self.branch)
            ws.apply_patches("llvm-test-suite", test_suite_path)

        clang_path = local_repo_path / 'tools/clang'
        if not clang_path.is_dir():
            ws.reference_clone(
                "https://llvm.org/git/clang",
                target_path=clang_path,
                branch=self.branch)
            ws.apply_patches("clang", clang_path)

        build_path = ws.build_dir / self.name / self.profile
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
            elif self.profile == "release":
                cmake_args += ["-DCMAKE_BUILD_TYPE=Release"]
            else:
                raise RuntimeException(
                    f"[LLVM] unknown profile: '{self.profile}' (available: 'debug', 'release')")

            _run(["cmake"] + cmake_args, cwd=build_path)

        _run(["cmake", "--build", "."], cwd=build_path)
