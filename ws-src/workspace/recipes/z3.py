from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2s
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, cast

import schema

from workspace.build_systems import CMakeConfig
from workspace.settings import settings
from workspace.util import env_prepend_path
from workspace.vcs.git import GitRecipeMixin

from .all_recipes import register_recipe
from .recipe import Recipe

if TYPE_CHECKING:
    from workspace import Workspace


class Z3(Recipe, GitRecipeMixin):  # pylint: disable=invalid-name
    """The [z3](https://github.com/Z3Prover/z3) constraint solver"""

    profiles = {
        "release": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Release',
            },
            "c_flags": [],
            "cxx_flags": [],
        },
        "rel+debinfo": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'RelWithDebInfo',
            },
            "c_flags": ["-fno-omit-frame-pointer"],
            "cxx_flags": ["-fno-omit-frame-pointer"],
        },
        "debug": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Debug',
            },
            "c_flags": [],
            "cxx_flags": [],
        },
    }

    default_arguments: Dict[str, Any] = {
        "name": "z3",
        "shared": True,
        "openmp": True,
        "cmake-adjustments": [],
    }

    argument_schema: Dict[str, Any] = {
        "profile": schema.Or(*profiles.keys()),
        "shared": bool,
        "openmp": bool,
        "cmake-adjustments": [str],
    }

    @property
    def profile(self) -> str:
        return self.arguments["profile"]

    @property
    def shared(self) -> bool:
        return self.arguments["shared"]

    @property
    def openmp(self) -> bool:
        return self.arguments["openmp"]

    @property
    def cmake_adjustments(self) -> List[str]:
        return self.arguments["cmake-adjustments"]

    def __init__(self, **kwargs):
        GitRecipeMixin.__init__(self, "github://Z3Prover/z3.git")
        Recipe.__init__(self, **kwargs)

        self.cmake = None
        self.paths = None

    def initialize(self, workspace: Workspace):
        def _compute_digest(self, workspace: Workspace):
            del workspace  # unused parameter

            digest = blake2s()
            digest.update(self.name.encode())
            digest.update(self.profile.encode())
            digest.update(f'shared:{self.shared}'.encode())
            digest.update(f'openmp:{self.openmp}'.encode())
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
                libz3: Path

            build_dir = workspace.build_dir / f'{self.name}-{self.profile}-{self.digest}'
            paths = InternalPaths(src_dir=settings.ws_path / self.name,
                                  build_dir=build_dir,
                                  libz3=build_dir / "libz3.so" if self.shared else build_dir / "libz3.a")
            return paths

        self.digest = _compute_digest(self, workspace)
        self.paths = _make_internal_paths(self, workspace)

        self.cmake = CMakeConfig(workspace)

    def setup(self, workspace: Workspace):
        self.setup_git(self.paths.src_dir, workspace.patch_dir / "z3")

    def _configure(self, workspace: Workspace):
        cxx_flags = cast(List[str], self.profiles[self.profile]["cxx_flags"])
        c_flags = cast(List[str], self.profiles[self.profile]["c_flags"])
        self.cmake.set_extra_c_flags(c_flags)
        self.cmake.set_extra_cxx_flags(cxx_flags)

        self.cmake.set_flag("BUILD_LIBZ3_SHARED", self.shared)
        self.cmake.set_flag("USE_OPENMP", self.openmp)

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


register_recipe(Z3)
