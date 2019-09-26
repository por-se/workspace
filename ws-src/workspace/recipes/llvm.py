from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

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
            "is_performance_build": True,
            "has_debug_info": False,
        },
        "rel+debinfo": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'RelWithDebInfo',
                'LLVM_ENABLE_ASSERTIONS': True,
            },
            "c_flags":
            ["-fno-omit-frame-pointer", "-g3", "-fvar-tracking", "-fvar-tracking-assignments", "-fdebug-types-section"],
            "cxx_flags":
            ["-fno-omit-frame-pointer", "-g3", "-fvar-tracking", "-fvar-tracking-assignments", "-fdebug-types-section"],
            "is_performance_build":
            True,
            "has_debug_info":
            True,
        },
        "debug": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Debug',
                'LLVM_ENABLE_ASSERTIONS': True,
            },
            "c_flags":
            ["-fno-omit-frame-pointer", "-g3", "-fvar-tracking", "-fvar-tracking-assignments", "-fdebug-types-section"],
            "cxx_flags":
            ["-fno-omit-frame-pointer", "-g3", "-fvar-tracking", "-fvar-tracking-assignments", "-fdebug-types-section"],
            "is_performance_build":
            False,
            "has_debug_info":
            True,
        },
    }

    default_arguments: Dict[str, Any] = {
        "z3": None,
    }

    argument_schema: Dict[str, Any] = {
        "z3": schema.Or(str, None),
    }

    def find_z3(self, workspace: Workspace) -> Optional[Z3]:
        if self.arguments["z3"] is None:
            return None
        return self._find_previous_build(workspace, "z3", Z3)

    def __init__(self, **kwargs):
        GitRecipeMixin.__init__(self, "github://llvm/llvm-project.git", sparse=["/llvm", "/clang"])
        CMakeRecipeMixin.__init__(self)
        Recipe.__init__(self, **kwargs)

        self._release_build: Optional[LLVM] = None

    def initialize(self, workspace: Workspace):
        Recipe.initialize(self, workspace)
        CMakeRecipeMixin.initialize(self, workspace)

        self.paths["tablegen"] = self.paths["build_dir"] / "bin" / "llvm-tblgen"
        self.paths["llvm-config"] = self.paths["build_dir"] / "bin" / "llvm-config"
        self.paths["llvm-lit"] = self.paths["build_dir"] / "bin" / "llvm-lit"
        self.paths["cmake_src_dir"] = self.paths["src_dir"] / "llvm"
        self.paths["cmake_export_dir"] = self.paths["build_dir"] / "lib" / "cmake" / "llvm"

        if not self.profile["is_performance_build"]:
            self._release_build = LLVM(
                name=self.name,
                repository=self.arguments["repository"],
                branch=self.branch,
                profile="release",
            )
            self._release_build.initialize(workspace)

    def compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        Recipe.compute_digest(self, workspace, digest)
        CMakeRecipeMixin.compute_digest(self, workspace, digest)

        z3 = self.find_z3(workspace)
        if z3:
            assert z3.shared, (f'[{self.name}] The {z3.__class__.__name__} build named "{z3.name}" '
                               f'must be built as shared to be usable by {self.__class__.__name__}')
            digest.update(z3.digest)
        else:
            digest.update("z3 disabled".encode())

    def setup(self, workspace: Workspace):
        if not self.profile["is_performance_build"]:
            assert self._release_build is not None
            self._release_build.setup(workspace)

        self.setup_git(self.paths["src_dir"], workspace.patch_dir / self.default_name)

    def configure(self, workspace: Workspace):
        CMakeRecipeMixin.configure(self, workspace)

        z3 = self.find_z3(workspace)
        if z3:
            self.cmake.set_flag('Z3_INCLUDE_DIRS', z3.paths["include_dir"])
            self.cmake.set_flag('Z3_LIBRARIES', z3.paths["libz3"])

        self.cmake.set_flag("LLVM_EXTERNAL_CLANG_SOURCE_DIR", self.paths["src_dir"] / "clang")
        self.cmake.set_flag("LLVM_TARGETS_TO_BUILD", "X86")
        self.cmake.set_flag("LLVM_INCLUDE_EXAMPLES", False)
        self.cmake.set_flag("HAVE_VALGRIND_VALGRIND_H", False)

        if not self.profile["is_performance_build"]:
            assert self._release_build is not None
            self.cmake.set_flag("LLVM_TABLEGEN", self._release_build.paths["tablegen"])

        avail_mem = psutil.virtual_memory().available
        if self.profile["has_debug_info"] and avail_mem < settings.jobs.value * 12000000000 and avail_mem < 35000000000:
            print(f'[{self.__class__.__name__}] less than 12G memory per thread (or 35G total) available '
                  'during a build containing debug information; '
                  'restricting link-parallelism to 1 [-DLLVM_PARALLEL_LINK_JOBS=1]')
            self.cmake.set_flag("LLVM_PARALLEL_LINK_JOBS", 1)

    def build(self, workspace: Workspace):
        if not self.profile["is_performance_build"]:
            assert self._release_build is not None
            self._release_build.build_target(workspace, target='bin/llvm-tblgen')

        CMakeRecipeMixin.build(self, workspace)

    def add_to_env(self, env, workspace: Workspace):
        env_prepend_path(env, "PATH", self.paths["build_dir"] / "bin")


register_recipe(LLVM)
