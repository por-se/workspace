import os, shutil
from hashlib import blake2s

from workspace.workspace import Workspace, _run
from workspace.util import j_from_num_threads, adjusted_cmake_args
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

    def initialize(self, ws: Workspace):
        def _compute_digest(self, ws: Workspace):
            digest = blake2s()
            digest.update(self.name.encode())

            # branch and repository need not be part of the digest, as we will build whatever
            # we find at the target path, no matter what it turns out to be at build time

            llvm = ws.find_build(build_name=self.llvm_name, before=self)
            assert llvm, "klee_uclibc requires llvm"
            digest.update(llvm.digest.encode())

            return digest.hexdigest()[:12]

        def _make_internal_paths(self, ws: Workspace):
            class InternalPaths:
                pass

            res = InternalPaths()
            res.local_repo_path = ws.ws_path / self.name
            return res

        self.digest = _compute_digest(self, ws)
        self.paths = _make_internal_paths(self, ws)

    def setup(self, ws: Workspace):
        local_repo_path = self.paths.local_repo_path
        if not local_repo_path.is_dir():
            ws.reference_clone(
                self.repository,
                target_path=local_repo_path,
                branch=self.branch)
            ws.apply_patches("klee-uclibc", local_repo_path)

    def build(self, ws: Workspace):
        local_repo_path = self.paths.local_repo_path

        if not (local_repo_path / '.config').exists():
            llvm = ws.find_build(build_name=self.llvm_name, before=self)
            assert llvm, "klee_uclibc requires llvm"

            _run([
                "./configure", "--make-llvm-lib",
                f"--with-llvm-config={llvm.build_output_path}/bin/llvm-config"
            ],
                 cwd=local_repo_path)

        _run(["make"] + j_from_num_threads(ws.args.num_threads), cwd=local_repo_path)

        self.repo_path = local_repo_path

    def clean(self, ws: Workspace):
        int_paths = self.paths
        if int_paths.local_repo_path.is_dir():
            if ws.args.dist_clean:
                shutil.rmtree(int_paths.local_repo_path)
            else:
                _run(["make", "distclean"], cwd=int_paths.local_repo_path)
