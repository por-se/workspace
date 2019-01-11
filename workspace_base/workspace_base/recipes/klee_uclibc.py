import os, shutil

from workspace_base.workspace import Workspace, _run
from workspace_base.util import j_from_num_threads
from . import Recipe
from .llvm import LLVM

from pathlib import Path


class KLEE_UCLIBC(Recipe):
    default_name = "klee-uclibc"

    def __init__(self,
                 branch,
                 repository="git@github.com:klee/klee-uclibc.git",
                 name=default_name,
                 llvm_name=LLVM.default_name):
        super().__init__(name)
        self.branch = branch
        self.llvm_name = llvm_name
        self.repository = repository

    def _make_internal_paths(self, ws: Workspace):
        class InternalPaths:
            pass

        res = InternalPaths()
        res.local_repo_path = ws.ws_path / self.name
        return res

    def build(self, ws: Workspace):
        int_paths = self._make_internal_paths(ws)

        local_repo_path = int_paths.local_repo_path
        if not local_repo_path.is_dir():
            ws.reference_clone(
                self.repository,
                target_path=local_repo_path,
                branch=self.branch)
            ws.apply_patches("klee-uclibc", local_repo_path)

        if not (local_repo_path / '.config').exists():
            llvm = ws.find_build(build_name=self.llvm_name, before=self)

            _run([
                "./configure", "--make-llvm-lib",
                f"--with-llvm-config={llvm.build_output_path}/bin/llvm-config"
            ],
                 cwd=local_repo_path)

        _run(["make"] + j_from_num_threads(ws.args.num_threads), cwd=local_repo_path)

        self.repo_path = local_repo_path

    def clean(self, ws: Workspace):
        int_paths = self._make_internal_paths(ws)
        if int_paths.local_repo_path.is_dir():
            if ws.args.dist_clean:
                shutil.rmtree(int_paths.local_repo_path)
            else:
                _run(["make", "distclean"], cwd=int_paths.local_repo_path)
