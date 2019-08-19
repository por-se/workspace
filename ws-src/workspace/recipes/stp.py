from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Dict

from workspace.build_systems import Linker
from workspace.build_systems.cmake_recipe_mixin import CMakeRecipeMixin
from workspace.util import env_prepend_path
from workspace.vcs.git import GitRecipeMixin

from .all_recipes import register_recipe
from .minisat import MINISAT
from .recipe import Recipe

if TYPE_CHECKING:
    import hashlib
    from workspace import Workspace


class STP(Recipe, GitRecipeMixin, CMakeRecipeMixin):  # pylint: disable=invalid-name
    profiles = {
        "release": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Release',
                'ENABLE_ASSERTIONS': True,
                'SANITIZE': False,
            },
        },
        "rel+debinfo": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'RelWithDebInfo',
                'ENABLE_ASSERTIONS': True,
                'SANITIZE': False,
            },
            "c_flags": ["-fno-omit-frame-pointer"],
            "cxx_flags": ["-fno-omit-frame-pointer"],
        },
        "debug": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Debug',
                'ENABLE_ASSERTIONS': True,
                'SANITIZE': False,
            },
        },
    }

    default_arguments: Dict[str, Any] = {
        "minisat": MINISAT().default_name,
    }

    argument_schema: Dict[str, Any] = {
        "minisat": str,
    }

    def find_minisat(self, workspace: Workspace) -> MINISAT:
        return self._find_previous_build(workspace, "minisat", MINISAT)

    def __init__(self, **kwargs):
        GitRecipeMixin.__init__(self, "github://stp/stp.git")
        CMakeRecipeMixin.__init__(self)
        Recipe.__init__(self, **kwargs)

    def initialize(self, workspace: Workspace):
        Recipe.initialize(self, workspace)
        CMakeRecipeMixin.initialize(self, workspace)

        if self.cmake.linker == Linker.LLD:
            msg = ("warning: linking STP with lld may cause crashes, falling back to gold.\n"
                   "         see https://laboratory.comsys.rwth-aachen.de/symbiosys/projects/workspace_base/issues/34")
            print(msg, file=sys.stderr)
            self.cmake.linker = Linker.GOLD

    def compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        Recipe.compute_digest(self, workspace, digest)
        CMakeRecipeMixin.compute_digest(self, workspace, digest)

        digest.update(self.find_minisat(workspace).digest)

    def configure(self, workspace: Workspace):
        CMakeRecipeMixin.configure(self, workspace)

        minisat = self.find_minisat(workspace)
        self.cmake.set_flag("MINISAT_LIBRARY", str(minisat.paths["build_dir"] / "libminisat.a"))
        self.cmake.set_flag("MINISAT_INCLUDE_DIR", str(minisat.paths["src_dir"]))

        self.cmake.set_flag("NOCRYPTOMINISAT", True)
        self.cmake.set_flag("STATICCOMPILE", True)
        self.cmake.set_flag("BUILD_SHARED_LIBS", False)
        self.cmake.set_flag("ENABLE_PYTHON_INTERFACE", False)

    def add_to_env(self, env, workspace: Workspace):
        env_prepend_path(env, "PATH", self.paths["build_dir"])


register_recipe(STP)
