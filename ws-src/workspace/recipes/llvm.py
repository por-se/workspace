from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

import psutil
import schema

from workspace.build_systems.cmake_recipe_mixin import CMakeRecipeMixin
from workspace.settings import settings
from workspace.util import env_prepend_path
from workspace.vcs.git import GitRecipeMixin

from .all_recipes import register_recipe
from .recipe import Recipe

if TYPE_CHECKING:
    import hashlib
    from workspace import Workspace
    from .z3 import Z3


class LLVM(Recipe, GitRecipeMixin, CMakeRecipeMixin):  # pylint: disable=invalid-name
    """
    The [LLVM Compiler Infrastructure](https://llvm.org/) and [clang](https://clang.llvm.org/)
    """

    profiles = {
        "release": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Release',
                'LLVM_ENABLE_ASSERTIONS': True,
            },
            "c_flags": [],
            "cxx_flags": [],
            "is_performance_build": True,
            "has_debug_info": False,
        },
        "rel+debinfo": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'RelWithDebInfo',
                'LLVM_ENABLE_ASSERTIONS': True,
            },
            "c_flags": ["-fno-omit-frame-pointer"],
            "cxx_flags": ["-fno-omit-frame-pointer"],
            "is_performance_build": True,
            "has_debug_info": True,
        },
        "debug": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Debug',
                'LLVM_ENABLE_ASSERTIONS': True,
            },
            "c_flags": [],
            "cxx_flags": [],
            "is_performance_build": False,
            "has_debug_info": True,
        },
    }

    default_arguments: Dict[str, Any] = {
        "z3": None,
    }

    argument_schema: Dict[str, Any] = {
        "profile": schema.Or(*profiles.keys()),
        "z3": schema.Or(str, None),
    }

    @property
    def profile(self) -> str:
        return self.arguments["profile"]

    def find_z3(self, workspace: Workspace) -> Optional[Z3]:
        if self.arguments["z3"] is None:
            return None
        return self._find_previous_build(workspace, "z3", Z3)

    def __init__(self, **kwargs):
        GitRecipeMixin.__init__(self, "github://llvm/llvm-project.git", sparse=["/llvm", "/clang"])
        CMakeRecipeMixin.__init__(self)
        Recipe.__init__(self, **kwargs)

        self._release_build: Optional[LLVM] = None

        self.paths = None

    def initialize(self, workspace: Workspace):
        Recipe.initialize(self, workspace)
        CMakeRecipeMixin.initialize(self, workspace)

        if not self.profiles[self.profile]["is_performance_build"]:
            self._release_build = LLVM(
                name=self.name,
                repository=self.arguments["repository"],
                branch=self.branch,
                profile="release",
            )
            self._release_build.initialize(workspace)

        @dataclass
        class InternalPaths:
            src_dir: Path
            build_dir: Path
            tablegen: Optional[Path] = None

        build_dir = workspace.build_dir / f'{self.name}-{self.profile}-{self.digest_str}'
        self.paths = InternalPaths(src_dir=settings.ws_path / self.name,
                                   build_dir=build_dir,
                                   tablegen=build_dir / "bin" / "llvm-tblgen")

    def compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        Recipe.compute_digest(self, workspace, digest)
        CMakeRecipeMixin.compute_digest(self, workspace, digest)

        digest.update(self.profile.encode())

        z3 = self.find_z3(workspace)
        if z3:
            assert z3.shared, (f'[{self.name}] The {z3.__class__.__name__} build named "{z3.name}" '
                               f'must be built as shared to be usable by {self.__class__.__name__}')
            digest.update(z3.digest)
        else:
            digest.update("z3 disabled".encode())

    def setup(self, workspace: Workspace):
        if not self.profiles[self.profile]["is_performance_build"]:
            assert self._release_build is not None
            self._release_build.setup(workspace)

        self.setup_git(self.paths.src_dir, workspace.patch_dir / "llvm")

    def _configure(self, workspace: Workspace):
        cxx_flags = cast(List[str], self.profiles[self.profile]["cxx_flags"])
        c_flags = cast(List[str], self.profiles[self.profile]["c_flags"])
        self.cmake.set_extra_c_flags(c_flags)
        self.cmake.set_extra_cxx_flags(cxx_flags)

        z3 = self.find_z3(workspace)
        if z3:
            self.cmake.set_flag('Z3_INCLUDE_DIRS', str(z3.paths.src_dir / "src/api/"))
            self.cmake.set_flag('Z3_LIBRARIES', str(z3.paths.libz3))

        self.cmake.set_flag("LLVM_EXTERNAL_CLANG_SOURCE_DIR", str(self.paths.src_dir / "clang"))
        self.cmake.set_flag("LLVM_TARGETS_TO_BUILD", "X86")
        self.cmake.set_flag("LLVM_INCLUDE_EXAMPLES", False)
        self.cmake.set_flag("HAVE_VALGRIND_VALGRIND_H", False)

        if not self.profiles[self.profile]["is_performance_build"]:
            assert self._release_build is not None
            self.cmake.set_flag("LLVM_TABLEGEN", str(self._release_build.paths.tablegen))

        avail_mem = psutil.virtual_memory().available
        if self.profiles[self.profile][
                "has_debug_info"] and avail_mem < settings.jobs.value * 12000000000 and avail_mem < 35000000000:
            print(f'[{self.__class__.__name__}] less than 12G memory per thread (or 35G total) available '
                  'during a build containing debug information; '
                  'restricting link-parallelism to 1 [-DLLVM_PARALLEL_LINK_JOBS=1]')
            self.cmake.set_flag("LLVM_PARALLEL_LINK_JOBS", 1)

        for name, value in cast(Dict, self.profiles[self.profile]["cmake_args"]).items():
            self.cmake.set_flag(name, value)
        self.cmake.adjust_flags(self.cmake_adjustments)

        self.cmake.configure(workspace, self.paths.src_dir / "llvm", self.paths.build_dir)

    def build_target(self, workspace: Workspace, target):
        if not self.profiles[self.profile]["is_performance_build"]:
            assert self._release_build is not None
            self._release_build.build_target(workspace, target='bin/llvm-tblgen')

        if not self.cmake.is_configured(workspace, self.paths.src_dir / "llvm", self.paths.build_dir):
            self._configure(workspace)
        self.cmake.build(workspace, self.paths.src_dir / "llvm", self.paths.build_dir, target=target)

    def build(self, workspace: Workspace):
        self.build_target(workspace, target=None)

    def add_to_env(self, env, workspace: Workspace):
        env_prepend_path(env, "PATH", self.paths.build_dir / "bin")


register_recipe(LLVM)
