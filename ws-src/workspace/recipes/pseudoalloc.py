from __future__ import annotations

from typing import TYPE_CHECKING

from workspace.build_systems.cmake_recipe_mixin import CMakeRecipeMixin
from workspace.vcs.git import GitRecipeMixin

from .all_recipes import register_recipe
from .recipe import Recipe

if TYPE_CHECKING:
    import hashlib
    from workspace import Workspace


class PSEUDOALLOC(Recipe, GitRecipeMixin, CMakeRecipeMixin):  # pylint: disable=invalid-name
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
        GitRecipeMixin.__init__(self, "laboratory://symbiosys/projects/concurrent-symbolic-execution/pseudoalloc.git")
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


register_recipe(PSEUDOALLOC)
