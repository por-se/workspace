import os, multiprocessing, shutil

from workspace.workspace import Workspace, _run
from workspace.util import j_from_num_threads, adjusted_cmake_args
from . import Recipe
from .llvm import LLVM

from pathlib import Path


class MINISAT(Recipe):
    default_name = "minisat"

    def __init__(self, branch, name=default_name, repository="git@github.com:stp/minisat.git", cmake_adjustments=[]):
        super().__init__(name)
        self.branch = branch
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
            ws.apply_patches("minisat", local_repo_path)

        build_path = int_paths.build_path
        if not build_path.exists():
            os.makedirs(build_path)
            cmake_args = adjusted_cmake_args(['-G', 'Ninja'], self.cmake_adjustments)
            _run(["cmake"] + cmake_args + [local_repo_path], cwd=build_path)

        _run(["cmake", "--build", "."] + j_from_num_threads(ws.args.num_threads), cwd=build_path)

        self.include_path = local_repo_path
        self.build_output_path = build_path

    def clean(self, ws: Workspace):
        int_paths = self._make_internal_paths(ws)
        if int_paths.build_path.is_dir():
            shutil.rmtree(int_paths.build_path)
        if ws.args.dist_clean and int_paths.local_repo_path.is_dir():
            shutil.rmtree(int_paths.local_repo_path)
