from __future__ import annotations

from typing import TYPE_CHECKING

from workspace.build_systems.cmake_recipe_mixin import CMakeRecipeMixin
from workspace.util import env_prepend_path
from workspace.vcs.git import GitRecipeMixin

from .all_recipes import register_recipe
from .recipe import Recipe

if TYPE_CHECKING:
    import hashlib
    from workspace import Workspace


class SIMULATOR(Recipe, GitRecipeMixin, CMakeRecipeMixin):  # pylint: disable=invalid-name
    """The libpor and simulator for PORSE"""

    profiles = {
        "release": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Release',
            },
        },
        "rel+debinfo": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'RelWithDebInfo',
            },
            "cxx_flags": ["-fno-omit-frame-pointer"],
        },
        "debug": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Debug',
            },
        },
        "sanitized": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Asan',
            },
        },
    }

    def __init__(self, **kwargs):
        GitRecipeMixin.__init__(self, "laboratory://symbiosys/projects/concurrent-symbolic-execution/simulator.git")
        CMakeRecipeMixin.__init__(self)
        Recipe.__init__(self, **kwargs)

    def initialize(self, workspace: Workspace):
        Recipe.initialize(self, workspace)
        CMakeRecipeMixin.initialize(self, workspace)

    def compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        Recipe.compute_digest(self, workspace, digest)
        CMakeRecipeMixin.compute_digest(self, workspace, digest)

    def configure(self, workspace: Workspace):
        CMakeRecipeMixin.configure(self, workspace)

    def add_to_env(self, env, workspace: Workspace):
        env_prepend_path(env, "PATH", self.paths["build_dir"] / "bin" / "random-graph")


register_recipe(SIMULATOR)
