from dataclasses import dataclass
from hashlib import blake2s
from pathlib import Path
import shutil
import subprocess

from workspace.workspace import Workspace
from workspace.settings import settings
from workspace.util import env_prepend_path
from . import Recipe, LLVM


class KLEE_UCLIBC(Recipe):  # pylint: disable=invalid-name,too-many-instance-attributes
    default_name = "klee-uclibc"

    def __init__(  # pylint: disable=too-many-arguments
            self,
            branch=None,
            repository="github://klee/klee-uclibc.git",
            name=default_name,
            llvm_name=LLVM.default_name):
        super().__init__(name)
        self.branch = branch
        self.llvm_name = llvm_name
        self.repository = repository

        self.paths = None

    def initialize(self, workspace: Workspace):
        def _compute_digest(self, workspace: Workspace):
            digest = blake2s()
            digest.update(self.name.encode())

            # branch and repository need not be part of the digest, as we will build whatever
            # we find at the target path, no matter what it turns out to be at build time

            llvm = workspace.find_build(build_name=self.llvm_name, before=self)
            assert llvm, "klee_uclibc requires llvm"
            digest.update(llvm.digest.encode())

            return digest.hexdigest()[:12]

        def _make_internal_paths(self, workspace: Workspace):
            @dataclass
            class InternalPaths:
                src_dir: Path
                build_dir: Path

            paths = InternalPaths(src_dir=workspace.ws_path / self.name,
                                  build_dir=workspace.build_dir / f'{self.name}-{self.digest}')
            return paths

        self.digest = _compute_digest(self, workspace)
        self.paths = _make_internal_paths(self, workspace)
        self.repository = Recipe.concretize_repo_uri(self.repository, workspace)

    def setup(self, workspace: Workspace):
        if not self.paths.src_dir.is_dir():
            workspace.git_add_exclude_path(self.paths.src_dir)
            workspace.reference_clone(self.repository, target_path=self.paths.src_dir, branch=self.branch)
            workspace.apply_patches("klee-uclibc", self.paths.src_dir)

    def build(self, workspace: Workspace):
        subprocess.run(["rsync", "-a", f'{self.paths.src_dir}/', self.paths.build_dir], check=True)

        env = workspace.get_env()

        if not (self.paths.build_dir / '.config').exists():
            llvm = workspace.find_build(build_name=self.llvm_name, before=self)
            assert llvm, "klee_uclibc requires llvm"

            subprocess.run(
                ["./configure", "--make-llvm-lib", f"--with-llvm-config={llvm.paths.build_dir}/bin/llvm-config"],
                cwd=self.paths.build_dir,
                env=env,
                check=True)

        subprocess.run(["make", "-j", str(settings.jobs.value)], cwd=self.paths.build_dir, env=env, check=True)

    def clean(self, workspace: Workspace):
        if workspace.args.dist_clean:
            if self.paths.src_dir.is_dir():
                shutil.rmtree(self.paths.src_dir)
            workspace.git_remove_exclude_path(self.paths.src_dir)

    def add_to_env(self, env, workspace: Workspace):
        env_prepend_path(env, "C_INCLUDE_PATH", self.paths.build_dir / "include")
