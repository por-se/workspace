from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2s
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

import schema

from workspace.build_systems import CMakeConfig
from workspace.settings import settings
from workspace.util import env_prepend_path

from .all_recipes import register_recipe
from .recipe import Recipe

if TYPE_CHECKING:
    from workspace import Workspace


class MINISAT(Recipe):  # pylint: disable=invalid-name
    default_arguments: Dict[str, Any] = {
        "name": "minisat",
        "repository": "github://stp/minisat.git",
        "branch": None,
        "cmake-adjustments": [],
    }

    argument_schema: Dict[str, Any] = {
        "name": str,
        "repository": str,
        "branch": schema.Or(str, None),
        "cmake-adjustments": [str],
    }

    @property
    def branch(self) -> str:
        return self.arguments["branch"]

    @property
    def cmake_adjustments(self) -> List[str]:
        return self.arguments["cmake-adjustments"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cmake = None
        self.paths = None
        self.repository = None

    def initialize(self, workspace: Workspace):
        def _compute_digest(self, workspace: Workspace):
            del workspace  # unused parameter

            digest = blake2s()
            digest.update(self.name.encode())
            for adjustment in self.cmake_adjustments:
                digest.update("CMAKE_ADJUSTMENT:".encode())
                digest.update(adjustment.encode())

            # branch and repository need not be part of the digest, as we will build whatever
            # we find at the target path, no matter what it turns out to be at build time

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

        self.cmake = CMakeConfig(workspace)

    def setup(self, workspace: Workspace):
        if not self.paths.src_dir.is_dir():
            workspace.git_add_exclude_path(self.paths.src_dir)
            workspace.reference_clone(self.repository, target_path=self.paths.src_dir, branch=self.branch)
            workspace.apply_patches("minisat", self.paths.src_dir)

    def _configure(self, workspace: Workspace):
        self.cmake.set_extra_cxx_flags(["-std=c++11"])
        self.cmake.adjust_flags(self.cmake_adjustments)

        self.cmake.configure(workspace, self.paths.src_dir, self.paths.build_dir)

    def build(self, workspace: Workspace):
        if not self.cmake.is_configured(workspace, self.paths.src_dir, self.paths.build_dir):
            self._configure(workspace)
        self.cmake.build(workspace, self.paths.src_dir, self.paths.build_dir)

    def add_to_env(self, env, workspace: Workspace):
        env_prepend_path(env, "PATH", self.paths.build_dir)


register_recipe(MINISAT)
