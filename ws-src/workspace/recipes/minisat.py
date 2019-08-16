from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

from workspace.build_systems import CMakeConfig
from workspace.settings import settings
from workspace.util import env_prepend_path
from workspace.vcs.git import GitRecipeMixin

from .all_recipes import register_recipe
from .recipe import Recipe

if TYPE_CHECKING:
    import hashlib
    from workspace import Workspace


class MINISAT(Recipe, GitRecipeMixin):  # pylint: disable=invalid-name
    default_arguments: Dict[str, Any] = {
        "name": "minisat",
        "cmake-adjustments": [],
    }

    argument_schema: Dict[str, Any] = {
        "cmake-adjustments": [str],
    }

    @property
    def cmake_adjustments(self) -> List[str]:
        return self.arguments["cmake-adjustments"]

    def __init__(self, **kwargs):
        GitRecipeMixin.__init__(self, "github://stp/minisat.git")
        Recipe.__init__(self, **kwargs)

        self.cmake = None
        self.paths = None

    def initialize(self, workspace: Workspace):
        Recipe.initialize(self, workspace)

        def _make_internal_paths(self, workspace: Workspace):
            @dataclass
            class InternalPaths:
                src_dir: Path
                build_dir: Path

            paths = InternalPaths(src_dir=settings.ws_path / self.name,
                                  build_dir=workspace.build_dir / f'{self.name}-{self.digest_str}')
            return paths

        self.paths = _make_internal_paths(self, workspace)

        self.cmake = CMakeConfig(workspace)

    def compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        Recipe.compute_digest(self, workspace, digest)

        for adjustment in self.cmake_adjustments:
            digest.update("CMAKE_ADJUSTMENT:".encode())
            digest.update(adjustment.encode())

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
