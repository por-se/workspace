from __future__ import annotations

import subprocess
from dataclasses import dataclass
from hashlib import blake2s
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

import schema

from workspace.settings import settings

from .all_recipes import register_recipe
from .llvm import LLVM
from .recipe import Recipe

if TYPE_CHECKING:
    from workspace import Workspace


class KLEE_UCLIBC(Recipe):  # pylint: disable=invalid-name
    default_arguments: Dict[str, Any] = {
        "name": "klee-uclibc",
        "repository": "github://klee/klee-uclibc.git",
        "branch": None,
        "llvm": LLVM.default_arguments["name"],
        "cmake-adjustments": [],
    }

    argument_schema: Dict[str, Any] = {
        "name": str,
        "repository": str,
        "branch": schema.Or(str, None),
        "llvm": str,
        "cmake-adjustments": [str],
    }

    @property
    def branch(self) -> str:
        return self.arguments["branch"]

    @property
    def cmake_adjustments(self) -> List[str]:
        return self.arguments["cmake-adjustments"]

    def find_llvm(self, workspace: Workspace) -> LLVM:
        return self._find_previous_build(workspace, "llvm", LLVM)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cmake = None
        self.paths = None
        self.repository = None

    def initialize(self, workspace: Workspace):
        def _compute_digest(self, workspace: Workspace):
            digest = blake2s()
            digest.update(self.name.encode())

            # branch and repository need not be part of the digest, as we will build whatever
            # we find at the target path, no matter what it turns out to be at build time

            digest.update(self.find_llvm(workspace).digest.encode())

            return digest.hexdigest()[:12]

        def _make_internal_paths(self, workspace: Workspace):
            @dataclass
            class InternalPaths:
                src_dir: Path
                build_dir: Path

            paths = InternalPaths(src_dir=settings.ws_path / self.name,
                                  build_dir=workspace.build_dir / f'{self.name}-{self.digest}')
            return paths

        self.digest = _compute_digest(self, workspace)
        self.paths = _make_internal_paths(self, workspace)
        self.repository = Recipe.concretize_repo_uri(self.arguments["repository"], workspace)

    def setup(self, workspace: Workspace):
        if not self.paths.src_dir.is_dir():
            workspace.git_add_exclude_path(self.paths.src_dir)
            workspace.reference_clone(self.repository, target_path=self.paths.src_dir, branch=self.branch)
            workspace.apply_patches("klee-uclibc", self.paths.src_dir)

    def build(self, workspace: Workspace):
        subprocess.run(["rsync", "-a", f'{self.paths.src_dir}/', self.paths.build_dir], check=True)

        env = workspace.get_env()

        if not (self.paths.build_dir / '.config').exists():
            llvm = self.find_llvm(workspace)

            subprocess.run(
                ["./configure", "--make-llvm-lib", f"--with-llvm-config={llvm.paths.build_dir}/bin/llvm-config"],
                cwd=self.paths.build_dir,
                env=env,
                check=True)

        subprocess.run(["make", "-j", str(settings.jobs.value)], cwd=self.paths.build_dir, env=env, check=True)


register_recipe(KLEE_UCLIBC)
