from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, cast

import schema

from workspace.build_systems.cmake_recipe_mixin import CMakeRecipeMixin
from workspace.settings import settings
from workspace.util import env_prepend_path
from workspace.vcs.git import GitRecipeMixin

from .all_recipes import register_recipe
from .klee_uclibc import KLEE_UCLIBC
from .llvm import LLVM
from .recipe import Recipe
from .stp import STP
from .z3 import Z3

if TYPE_CHECKING:
    import hashlib
    from workspace import Workspace


class KLEE(Recipe, GitRecipeMixin, CMakeRecipeMixin):  # pylint: disable=invalid-name
    """
    The [KLEE LLVM Execution Engine](https://klee.github.io/)
    """

    profiles = {
        "release": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Release',
                'KLEE_RUNTIME_BUILD_TYPE': 'Release+Asserts',
                'ENABLE_TCMALLOC': True,
            },
            "c_flags": [],
            "cxx_flags": [],
        },
        "rel+debinfo": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'RelWithDebInfo',
                'KLEE_RUNTIME_BUILD_TYPE': 'Release+Debug+Asserts',
                'ENABLE_TCMALLOC': True,
            },
            "c_flags": ["-fno-omit-frame-pointer"],
            "cxx_flags": ["-fno-omit-frame-pointer"],
        },
        "debug": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Debug',
                'KLEE_RUNTIME_BUILD_TYPE': 'Debug+Asserts',
                'ENABLE_TCMALLOC': True,
            },
            "c_flags": [],
            "cxx_flags": [],
        },
        "sanitized": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Debug',
                'KLEE_RUNTIME_BUILD_TYPE': 'Release+Asserts',
                'ENABLE_TCMALLOC': False,
            },
            "c_flags": ["-fsanitize=address", "-fsanitize=undefined"],
            "cxx_flags": ["-fsanitize=address", "-fsanitize=undefined"],
        },
    }

    default_arguments: Dict[str, Any] = {
        "klee-uclibc": KLEE_UCLIBC().default_name,
        "llvm": LLVM().default_name,
        "z3": Z3().default_name,
        "stp": STP().default_name,
    }

    argument_schema: Dict[str, Any] = {
        "profile": schema.Or(*profiles.keys()),
        "klee-uclibc": str,
        "llvm": str,
        "z3": str,
        "stp": str,
    }

    @property
    def profile(self) -> str:
        return self.arguments["profile"]

    def find_klee_uclibc(self, workspace: Workspace) -> KLEE_UCLIBC:
        return self._find_previous_build(workspace, "klee-uclibc", KLEE_UCLIBC)

    def find_llvm(self, workspace: Workspace) -> LLVM:
        return self._find_previous_build(workspace, "llvm", LLVM)

    def find_z3(self, workspace: Workspace) -> Z3:
        return self._find_previous_build(workspace, "z3", Z3)

    def find_stp(self, workspace: Workspace) -> STP:
        return self._find_previous_build(workspace, "stp", STP)

    def __init__(self, **kwargs):
        GitRecipeMixin.__init__(self, "github://klee/klee.git")
        CMakeRecipeMixin.__init__(self)
        Recipe.__init__(self, **kwargs)

        self.paths = None

    def initialize(self, workspace: Workspace) -> None:
        Recipe.initialize(self, workspace)
        CMakeRecipeMixin.initialize(self, workspace)

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
        digest.update(self.find_stp(workspace).digest)
        digest.update(self.find_z3(workspace).digest)
        digest.update(self.find_llvm(workspace).digest)
        digest.update(self.find_klee_uclibc(workspace).digest)

    def setup(self, workspace: Workspace):
        self.setup_git(self.paths.src_dir, workspace.patch_dir / "klee")

    def _configure(self, workspace: Workspace):
        cxx_flags = cast(List[str], self.profiles[self.profile]["cxx_flags"])
        c_flags = cast(List[str], self.profiles[self.profile]["c_flags"])
        self.cmake.set_extra_c_flags(c_flags)
        self.cmake.set_extra_cxx_flags(cxx_flags)

        stp = self.find_stp(workspace)
        z3 = self.find_z3(workspace)
        llvm = self.find_llvm(workspace)
        klee_uclibc = self.find_klee_uclibc(workspace)

        self.cmake.set_flag('USE_CMAKE_FIND_PACKAGE_LLVM', True)
        self.cmake.set_flag('LLVM_DIR', str(llvm.paths.build_dir / "lib/cmake/llvm/"))
        self.cmake.set_flag('ENABLE_SOLVER_STP', True)
        self.cmake.set_flag('STP_DIR', str(stp.paths.src_dir))
        self.cmake.set_flag('STP_STATIC_LIBRARY', str(stp.paths.build_dir / "lib/libstp.a"))
        self.cmake.set_flag('ENABLE_SOLVER_Z3', True)
        self.cmake.set_flag('Z3_INCLUDE_DIRS', str(z3.paths.src_dir / "src/api/"))
        self.cmake.set_flag('Z3_LIBRARIES', str(z3.paths.libz3))
        self.cmake.set_flag('ENABLE_POSIX_RUNTIME', True)
        self.cmake.set_flag('ENABLE_KLEE_UCLIBC', True)
        self.cmake.set_flag('KLEE_UCLIBC_PATH', str(klee_uclibc.paths.build_dir))

        lit = shutil.which("lit")
        assert lit, "lit is not installed"
        self.cmake.set_flag('LIT_TOOL', lit)

        self.cmake.set_flag('ENABLE_SYSTEM_TESTS', True)
        self.cmake.set_flag('ENABLE_UNIT_TESTS', True)

        for name, value in cast(Dict, self.profiles[self.profile]["cmake_args"]).items():
            self.cmake.set_flag(name, value)
        self.cmake.adjust_flags(self.cmake_adjustments)

        self.cmake.configure(workspace, self.paths.src_dir, self.paths.build_dir)

    def build(self, workspace: Workspace):
        if not self.cmake.is_configured(workspace, self.paths.src_dir, self.paths.build_dir):
            self._configure(workspace)
        self.cmake.build(workspace, self.paths.src_dir, self.paths.build_dir)

    def add_to_env(self, env, workspace: Workspace):
        env_prepend_path(env, "PATH", self.paths.build_dir / "bin")
        env_prepend_path(env, "C_INCLUDE_PATH", self.paths.src_dir / "include")


register_recipe(KLEE)
