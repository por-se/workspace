from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from workspace.build_systems.cmake_recipe_mixin import CMakeRecipeMixin
from workspace.settings import settings
from workspace.util import env_prepend_path
from workspace.vcs.git import GitRecipeMixin

from .all_recipes import register_recipe
from .recipe import Recipe

if TYPE_CHECKING:
    import hashlib
    from workspace import Workspace


class MINISAT(Recipe, GitRecipeMixin, CMakeRecipeMixin):  # pylint: disable=invalid-name
    def __init__(self, **kwargs):
        GitRecipeMixin.__init__(self, "github://stp/minisat.git")
        CMakeRecipeMixin.__init__(self)
        Recipe.__init__(self, **kwargs)

        self.paths = None

    def initialize(self, workspace: Workspace):
        Recipe.initialize(self, workspace)
        CMakeRecipeMixin.initialize(self, workspace)

        @dataclass
        class InternalPaths:
            src_dir: Path
            build_dir: Path

        self.paths = InternalPaths(src_dir=settings.ws_path / self.name,
                                   build_dir=workspace.build_dir / f'{self.name}-{self.digest_str}')

    def compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        Recipe.compute_digest(self, workspace, digest)
        CMakeRecipeMixin.compute_digest(self, workspace, digest)

    def setup(self, workspace: Workspace):
        self.setup_git(self.paths.src_dir, workspace.patch_dir / "minisat")

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
