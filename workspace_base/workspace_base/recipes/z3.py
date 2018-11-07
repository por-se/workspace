import os

from workspace_base.workspace import Workspace, _run
from . import Recipe

from pathlib import Path


class Z3(Recipe):
    def __init__(self, branch, profile, name="z3"):
        super().__init__(name)
        self.branch = branch
        self.profile = profile

    def build(self, ws: Workspace):
        local_repo_path = ws.ws_path / self.name

        if not local_repo_path.is_dir():
            ws.reference_clone(
                "git@github.com:Z3Prover/z3.git",
                target_path=local_repo_path,
                branch=self.branch)
            ws.apply_patches("z3", local_repo_path)

        build_path = ws.build_dir / self.name / self.profile
        if not build_path.exists():
            os.makedirs(build_path)

            cmake_args = [
                '-G', 'Ninja', '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
                '-DBUILD_LIBZ3_SHARED=false', '-DUSE_OPENMP=0',
                '-DCMAKE_CXX_FLAGS=-fuse-ld=gold -fdiagnostics-color=always',
                local_repo_path
            ]

            if self.profile == "release":
                cmake_args += ["-DCMAKE_BUILD_TYPE=Release"]
            else:
                raise RuntimeException(
                    f"[Z3] unknown profile: '{self.profile}' (available: 'release')")

            _run(["cmake"] + cmake_args, cwd=build_path)

        _run(["cmake", "--build", "."], cwd=build_path)
