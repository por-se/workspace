import os, shutil
from hashlib import blake2s

from workspace.workspace import Workspace, _run
from workspace.util import j_from_num_threads
from . import Recipe, LLVM

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

            paths = InternalPaths()
            paths.src_dir = ws.ws_path / self.name
            paths.build_dir = ws.build_dir / f'{self.name}-{self.digest}'
            return paths

        self.digest = _compute_digest(self, ws)
        self.paths = _make_internal_paths(self, ws)

    def setup(self, ws: Workspace):
        if not self.paths.src_dir.is_dir():
            ws.git_add_exclude_path(self.paths.src_dir)
            ws.reference_clone(
                self.repository,
                target_path=self.paths.src_dir,
                branch=self.branch)
            ws.apply_patches("klee-uclibc", self.paths.src_dir)

    def build(self, ws: Workspace):
        _run(["rsync", "-a", f'{self.paths.src_dir}/', self.paths.build_dir])

        if not (self.paths.build_dir / '.config').exists():
            llvm = ws.find_build(build_name=self.llvm_name, before=self)
            assert llvm, "klee_uclibc requires llvm"

            _run([
                "./configure", "--make-llvm-lib",
                f"--with-llvm-config={llvm.paths.build_dir}/bin/llvm-config"
            ], cwd=self.paths.build_dir)

        _run(["make"] + j_from_num_threads(ws.args.num_threads), cwd=self.paths.build_dir)

    def clean(self, ws: Workspace):
        if ws.args.dist_clean:
            if self.paths.src_dir.is_dir():
                shutil.rmtree(self.paths.src_dir)
            ws.git_remove_exclude_path(self.paths.src_dir)
        else:
            if self.paths.src_dir.is_dir():
                _run(["make", "distclean"], cwd=self.paths.src_dir)
