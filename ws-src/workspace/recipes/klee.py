from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from workspace.build_systems.cmake_recipe_mixin import CMakeRecipeMixin
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
        },
        "rel+debinfo": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'RelWithDebInfo',
                'KLEE_RUNTIME_BUILD_TYPE': 'Release+Debug+Asserts',
                'ENABLE_TCMALLOC': True,
            },
            "c_flags":
            ["-fno-omit-frame-pointer", "-g3", "-fvar-tracking", "-fvar-tracking-assignments", "-fdebug-types-section"],
            "cxx_flags":
            ["-fno-omit-frame-pointer", "-g3", "-fvar-tracking", "-fvar-tracking-assignments", "-fdebug-types-section"],
        },
        "debug": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Debug',
                'KLEE_RUNTIME_BUILD_TYPE': 'Debug+Asserts',
                'ENABLE_TCMALLOC': True,
            },
            "c_flags":
            ["-fno-omit-frame-pointer", "-g3", "-fvar-tracking", "-fvar-tracking-assignments", "-fdebug-types-section"],
            "cxx_flags":
            ["-fno-omit-frame-pointer", "-g3", "-fvar-tracking", "-fvar-tracking-assignments", "-fdebug-types-section"],
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
        "vptr-sanitizer": False,
    }

    argument_schema: Dict[str, Any] = {
        "klee-uclibc": str,
        "llvm": str,
        "z3": str,
        "stp": str,
        "vptr-sanitizer": bool,
    }

    @property
    def vptr_sanitizer(self) -> bool:
        return self.arguments["vptr-sanitizer"]

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

    def initialize(self, workspace: Workspace) -> None:
        Recipe.initialize(self, workspace)
        CMakeRecipeMixin.initialize(self, workspace)

        if self.vptr_sanitizer:
            llvm = self.find_llvm(workspace)
            if not llvm.rtti:
                raise Exception(f'[{self.name}] The {llvm.__class__.__name__} build named "{llvm.name}" '
                                f'must be built with RTTI to be usable by {self.__class__.__name__} '
                                f'with vptr sanitizer enabled')

    def compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        Recipe.compute_digest(self, workspace, digest)
        CMakeRecipeMixin.compute_digest(self, workspace, digest)

        digest.update(self.find_stp(workspace).digest)
        digest.update(self.find_z3(workspace).digest)
        digest.update(self.find_llvm(workspace).digest)
        digest.update(self.find_klee_uclibc(workspace).digest)

        digest.update(f'vptr-sanitizer:{self.vptr_sanitizer}'.encode())

    def configure(self, workspace: Workspace):
        CMakeRecipeMixin.configure(self, workspace)

        stp = self.find_stp(workspace)
        z3 = self.find_z3(workspace)
        llvm = self.find_llvm(workspace)
        klee_uclibc = self.find_klee_uclibc(workspace)

        self.cmake.set_flag('USE_CMAKE_FIND_PACKAGE_LLVM', True)
        self.cmake.set_flag('LLVM_DIR', llvm.paths["cmake_export_dir"])
        self.cmake.set_flag('LIT_TOOL', llvm.paths["llvm-lit"])
        self.cmake.set_flag('ENABLE_SOLVER_STP', True)
        self.cmake.set_flag('STP_DIR', stp.paths["src_dir"])
        self.cmake.set_flag('STP_STATIC_LIBRARY', stp.paths["libstp"])
        self.cmake.set_flag('ENABLE_SOLVER_Z3', True)
        self.cmake.set_flag('Z3_INCLUDE_DIRS', z3.paths["include_dir"])
        self.cmake.set_flag('Z3_LIBRARIES', z3.paths["libz3"])
        self.cmake.set_flag('ENABLE_POSIX_RUNTIME', True)
        self.cmake.set_flag('ENABLE_KLEE_UCLIBC', True)
        self.cmake.set_flag('KLEE_UCLIBC_PATH', klee_uclibc.paths["build_dir"])

        self.cmake.set_flag('ENABLE_SYSTEM_TESTS', True)
        self.cmake.set_flag('ENABLE_UNIT_TESTS', True)

        if self.vptr_sanitizer:
            cxx_flags = self.profile["cxx_flags"].copy()
            cxx_flags.append("-fsanitize=vptr")
            self.cmake.set_extra_cxx_flags(cxx_flags)

    def add_to_env(self, env, workspace: Workspace):
        env_prepend_path(env, "PATH", self.paths["build_dir"] / "bin")
        env_prepend_path(env, "C_INCLUDE_PATH", self.paths["src_dir"] / "include")


register_recipe(KLEE)
