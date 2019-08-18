from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, cast

import schema

from workspace.build_systems import Linker
from workspace.build_systems.cmake_recipe_mixin import CMakeRecipeMixin
from workspace.settings import settings
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
            "c_flags": [],
            "cxx_flags": [],
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
            "c_flags": [],
            "cxx_flags": [],
        },
    }

    default_arguments: Dict[str, Any] = {
        "minisat": MINISAT().default_name,
    }

    argument_schema: Dict[str, Any] = {
        "profile": schema.Or(*profiles.keys()),
        "minisat": str,
    }

    @property
    def profile(self) -> str:
        return self.arguments["profile"]

    def find_minisat(self, workspace: Workspace) -> MINISAT:
        return self._find_previous_build(workspace, "minisat", MINISAT)

    def __init__(self, **kwargs):
        GitRecipeMixin.__init__(self, "github://stp/stp.git")
        CMakeRecipeMixin.__init__(self)
        Recipe.__init__(self, **kwargs)

        self.paths = None

    def initialize(self, workspace: Workspace):
        Recipe.initialize(self, workspace)
        CMakeRecipeMixin.initialize(self, workspace)

        if self.cmake.linker == Linker.LLD:
            msg = ("warning: linking STP with lld may cause crashes, falling back to gold.\n"
                   "         see https://laboratory.comsys.rwth-aachen.de/symbiosys/projects/workspace_base/issues/34")
            print(msg, file=sys.stderr)
            self.cmake.linker = Linker.GOLD

        @dataclass
        class InternalPaths:
            src_dir: Path
            build_dir: Path

        self.paths = InternalPaths(src_dir=settings.ws_path / self.name,
                                   build_dir=workspace.build_dir / f'{self.name}-{self.profile}-{self.digest_str}')

    def compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        Recipe.compute_digest(self, workspace, digest)
        CMakeRecipeMixin.compute_digest(self, workspace, digest)

        digest.update(self.profile.encode())
        digest.update(self.find_minisat(workspace).digest)

    def setup(self, workspace: Workspace):
        self.setup_git(self.paths.src_dir, workspace.patch_dir / "stp")

    def _configure(self, workspace: Workspace):
        cxx_flags = cast(List[str], self.profiles[self.profile]["cxx_flags"])
        c_flags = cast(List[str], self.profiles[self.profile]["c_flags"])
        self.cmake.set_extra_c_flags(c_flags)
        self.cmake.set_extra_cxx_flags(cxx_flags)

        minisat = self.find_minisat(workspace)
        self.cmake.set_flag("MINISAT_LIBRARY", f"{minisat.paths.build_dir}/libminisat.a")
        self.cmake.set_flag("MINISAT_INCLUDE_DIR", str(minisat.paths.src_dir))

        self.cmake.set_flag("NOCRYPTOMINISAT", True)
        self.cmake.set_flag("STATICCOMPILE", True)
        self.cmake.set_flag("BUILD_SHARED_LIBS", False)
        self.cmake.set_flag("ENABLE_PYTHON_INTERFACE", False)

        for name, value in cast(Dict, self.profiles[self.profile]["cmake_args"]).items():
            self.cmake.set_flag(name, value)
        self.cmake.adjust_flags(self.cmake_adjustments)

        self.cmake.configure(workspace, self.paths.src_dir, self.paths.build_dir)

    def build(self, workspace: Workspace):
        if not self.cmake.is_configured(workspace, self.paths.src_dir, self.paths.build_dir):
            self._configure(workspace)
        self.cmake.build(workspace, self.paths.src_dir, self.paths.build_dir)

    def add_to_env(self, env, workspace: Workspace):
        env_prepend_path(env, "PATH", self.paths.build_dir)


register_recipe(STP)
