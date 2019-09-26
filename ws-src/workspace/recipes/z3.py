from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from workspace.build_systems.cmake_recipe_mixin import CMakeRecipeMixin
from workspace.util import env_prepend_path
from workspace.vcs.git import GitRecipeMixin

from .all_recipes import register_recipe
from .recipe import Recipe

if TYPE_CHECKING:
    import hashlib
    from workspace import Workspace


class Z3(Recipe, GitRecipeMixin, CMakeRecipeMixin):  # pylint: disable=invalid-name
    """The [z3](https://github.com/Z3Prover/z3) constraint solver"""

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
            "c_flags":
            ["-fno-omit-frame-pointer", "-g3", "-fvar-tracking", "-fvar-tracking-assignments", "-fdebug-types-section"],
            "cxx_flags":
            ["-fno-omit-frame-pointer", "-g3", "-fvar-tracking", "-fvar-tracking-assignments", "-fdebug-types-section"],
        },
        "debug": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Debug',
            },
            "c_flags":
            ["-fno-omit-frame-pointer", "-g3", "-fvar-tracking", "-fvar-tracking-assignments", "-fdebug-types-section"],
            "cxx_flags":
            ["-fno-omit-frame-pointer", "-g3", "-fvar-tracking", "-fvar-tracking-assignments", "-fdebug-types-section"],
        },
    }

    default_arguments: Dict[str, Any] = {
        "shared": True,
        "openmp": True,
    }

    argument_schema: Dict[str, Any] = {
        "shared": bool,
        "openmp": bool,
    }

    @property
    def shared(self) -> bool:
        return self.arguments["shared"]

    @property
    def openmp(self) -> bool:
        return self.arguments["openmp"]

    def __init__(self, **kwargs):
        GitRecipeMixin.__init__(self, "github://Z3Prover/z3.git")
        CMakeRecipeMixin.__init__(self)
        Recipe.__init__(self, **kwargs)

    def initialize(self, workspace: Workspace):
        Recipe.initialize(self, workspace)
        CMakeRecipeMixin.initialize(self, workspace)

        if self.shared:
            self.paths["libz3"] = self.paths["build_dir"] / "libz3.so"
        else:
            self.paths["libz3"] = self.paths["build_dir"] / "libz3.a"

        self.paths["include_dir"] = self.paths["src_dir"] / "src" / "api"

    def compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        Recipe.compute_digest(self, workspace, digest)
        CMakeRecipeMixin.compute_digest(self, workspace, digest)

        digest.update(f'shared:{self.shared}'.encode())
        digest.update(f'openmp:{self.openmp}'.encode())

    def configure(self, workspace: Workspace):
        CMakeRecipeMixin.configure(self, workspace)

        self.cmake.set_flag("BUILD_LIBZ3_SHARED", self.shared)
        self.cmake.set_flag("USE_OPENMP", self.openmp)

    def add_to_env(self, env, workspace: Workspace):
        env_prepend_path(env, "PATH", self.paths["build_dir"])


register_recipe(Z3)
