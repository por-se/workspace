from __future__ import annotations

from pathlib import Path
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
        "lto": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Release',
                'Z3_LINK_TIME_OPTIMIZATION': True,
            },
        },
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
        "gmp": True,
        "shared": True,
        "thread-safe": True,
    }

    argument_schema: Dict[str, Any] = {
        "gmp": bool,
        "shared": bool,
        "thread-safe": bool,
    }

    @property
    def gmp(self) -> bool:
        return self.arguments["gmp"]

    @property
    def shared(self) -> bool:
        return self.arguments["shared"]

    @property
    def thread_safe(self) -> bool:
        return self.arguments["thread-safe"]

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

        digest.update(f'gmp:{self.gmp}'.encode())
        digest.update(f'shared:{self.shared}'.encode())
        digest.update(f'thread-safe:{self.thread_safe}'.encode())

    def configure(self, workspace: Workspace):
        CMakeRecipeMixin.configure(self, workspace)

        self.cmake.set_flag("Z3_BUILD_LIBZ3_SHARED", self.shared)
        self.cmake.set_flag("Z3_USE_LIB_GMP", self.gmp)
        # renamed on master to Z3_SINGLE_THREADED
        self.cmake.set_flag("SINGLE_THREADED", not self.thread_safe)

    def build(self, workspace: Workspace):
        CMakeRecipeMixin.build(self, workspace)

        with open(self.paths["build_dir"] / "CMakeCache.txt") as f:
            for line in f:
                if line.startswith("GMP_CXX_LIBRARIES:FILEPATH="):
                    self.paths["libgmpxx"] = Path(line[len("GMP_CXX_LIBRARIES:FILEPATH="):].strip())
                if line.startswith("GMP_C_LIBRARIES:FILEPATH="):
                    self.paths["libgmp"] = Path(line[len("GMP_C_LIBRARIES:FILEPATH="):].strip())

    def add_to_env(self, env, workspace: Workspace):
        env_prepend_path(env, "PATH", self.paths["build_dir"])


register_recipe(Z3)
