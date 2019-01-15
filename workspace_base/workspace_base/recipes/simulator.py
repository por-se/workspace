import os, shutil

from workspace_base.workspace import Workspace, _run
from workspace_base.util import j_from_num_threads, adjusted_cmake_args
from . import Recipe

from pathlib import Path


class SIMULATOR(Recipe):
    default_name = "simulator"

    def __init__(self, branch, profile, repository="git@laboratory.comsys.rwth-aachen.de:concurrent-symbolic-execution/simulator.git", name=default_name, cmake_adjustments=[]):
        super().__init__(name)
        self.branch = branch
        self.profile = profile
        self.repository = repository
        self.cmake_adjustments = cmake_adjustments

    def _make_internal_paths(self, ws: Workspace):
        class InternalPaths:
            pass

        res = InternalPaths()
        res.local_repo_path = ws.ws_path / self.name
        res.build_path = ws.build_dir / self.name
        return res

    def build(self, ws: Workspace):
        int_paths = self._make_internal_paths(ws)

        local_repo_path = int_paths.local_repo_path
        if not local_repo_path.is_dir():
            ws.reference_clone(
                self.repository,
                target_path=local_repo_path,
                branch=self.branch)
            ws.apply_patches("simulator", local_repo_path)

        build_path = int_paths.build_path
        if not build_path.exists():
            os.makedirs(build_path)

            cmake_args = [
                '-G', 'Ninja', '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
                '-DCMAKE_CXX_FLAGS=-fuse-ld=gold -fdiagnostics-color=always',
            ]

            if self.profile == "release":
                cmake_args += ["-DCMAKE_BUILD_TYPE=Release"]
            else:
                raise RuntimeException(
                    f"[{self.name}] unknown profile: '{self.profile}' (available: 'release')")

            cmake_args = adjusted_cmake_args(cmake_args, self.cmake_adjustments)

            _run(["cmake"] + cmake_args + [local_repo_path], cwd=build_path)

        _run(["cmake", "--build", "."] + j_from_num_threads(ws.args.num_threads), cwd=build_path)

        self.z3_dir = local_repo_path
        self.build_output_path = build_path

        self.repo_path = local_repo_path

    def clean(self, ws: Workspace):
        int_paths = self._make_internal_paths(ws)
        if int_paths.build_path.is_dir():
            shutil.rmtree(int_paths.build_path)
        if ws.args.dist_clean and int_paths.local_repo_path.is_dir():
            shutil.rmtree(int_paths.local_repo_path)
