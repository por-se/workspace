import os, multiprocessing

from workspace_base.workspace import Workspace, _run
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

    def build(self, ws: Workspace):
        local_repo_path = ws.ws_path / self.name

        if not local_repo_path.is_dir():
            ws.reference_clone(
                self.repository,
                target_path=local_repo_path,
                branch=self.branch)
            ws.apply_patches("klee-uclibc", local_repo_path)

            llvm = ws.find_build(build_name=self.llvm_name, before=self)

            _run([
                "./configure", "--make-llvm-lib",
                f"--with-llvm-config={llvm.build_output_path}/bin/llvm-config"
            ],
                 cwd=local_repo_path)

            _run(["make", "-j", str(multiprocessing.cpu_count())], cwd=local_repo_path)
