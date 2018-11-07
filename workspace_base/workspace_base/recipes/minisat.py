import os, multiprocessing

from workspace_base.workspace import Workspace, _run
from . import Recipe
from .llvm import LLVM

from pathlib import Path


class MINISAT(Recipe):
    default_name = "minisat"

    def __init__(self, branch, name=default_name, repository="git@github.com:stp/minisat.git"):
        super().__init__(name)
        self.branch = branch
        self.repository = repository

    def build(self, ws: Workspace):
        local_repo_path = ws.ws_path / self.name

        if not local_repo_path.is_dir():
            ws.reference_clone(
                self.repository,
                target_path=local_repo_path,
                branch=self.branch)
            ws.apply_patches("minisat", local_repo_path)

        build_path = ws.build_dir / self.name / 'release'
        if not build_path.exists():
            os.makedirs(build_path)

            cmake_args = ['-G', 'Ninja', local_repo_path]

            _run(["cmake"] + cmake_args, cwd=build_path)

        _run(["cmake", "--build", "."], cwd=build_path)

        self.build_output_path = build_path
