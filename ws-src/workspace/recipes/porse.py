from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

import schema

from workspace.build_systems.cmake_recipe_mixin import CMakeRecipeMixin
from workspace.util import env_prepend_path
from workspace.vcs.git import GitRecipeMixin

from .all_recipes import register_recipe
from .klee_libcxx import KLEE_LIBCXX
from .klee_uclibc import KLEE_UCLIBC
from .llvm import LLVM
from .recipe import Recipe
from .stp import STP
from .z3 import Z3

if TYPE_CHECKING:
    import hashlib
    from workspace import Workspace


class PORSE(Recipe, GitRecipeMixin, CMakeRecipeMixin):  # pylint: disable=invalid-name
    """
    The KLEE-based PORSE tool (POR = Partial Order Reduction, SE = Symbolic Execution)
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
        "klee-libcxx": None,
        "verified-fingerprints": False,
        "vptr-sanitizer": False,
    }

    argument_schema: Dict[str, Any] = {
        "klee-uclibc": str,
        "llvm": str,
        "z3": str,
        "stp": str,
        "klee-libcxx": schema.Or(str, None),
        "verified-fingerprints": bool,
        "vptr-sanitizer": bool,
    }

    def find_klee_uclibc(self, workspace: Workspace) -> KLEE_UCLIBC:
        return self._find_previous_build(workspace, "klee-uclibc", KLEE_UCLIBC)

    def find_llvm(self, workspace: Workspace) -> LLVM:
        return self._find_previous_build(workspace, "llvm", LLVM)

    def find_z3(self, workspace: Workspace) -> Z3:
        return self._find_previous_build(workspace, "z3", Z3)

    def find_stp(self, workspace: Workspace) -> STP:
        return self._find_previous_build(workspace, "stp", STP)

    def find_klee_libcxx(self, workspace: Workspace) -> Optional[KLEE_LIBCXX]:
        if self.arguments["klee-libcxx"] is None:
            return None
        return self._find_previous_build(workspace, "klee-libcxx", KLEE_LIBCXX)

    @property
    def verified_fingerprints(self) -> bool:
        return self.arguments["verified-fingerprints"]

    @property
    def vptr_sanitizer(self) -> bool:
        return self.arguments["vptr-sanitizer"]

    def __init__(self, **kwargs):
        GitRecipeMixin.__init__(self,
                                "laboratory://symbiosys/projects/concurrent-symbolic-execution/klee.git",
                                upstream="github://klee/klee.git")
        CMakeRecipeMixin.__init__(self)
        Recipe.__init__(self, **kwargs)

    def initialize(self, workspace: Workspace) -> None:
        Recipe.initialize(self, workspace)
        CMakeRecipeMixin.initialize(self, workspace)

        llvm = self.find_llvm(workspace)

        if llvm.include_tests:
            raise Exception(f'[{self.name}] The {llvm.__class__.__name__} build named "{llvm.name}" '
                            f'must be built with "include tests" set to "false" to prevent {self.__class__.__name__} '
                            f'from reusing LLVM\'s Google Test targets')

        if self.vptr_sanitizer:
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

        klee_libcxx = self.find_klee_libcxx(workspace)
        if klee_libcxx:
            digest.update(klee_libcxx.digest)

        digest.update(f'verified-fingerprints:{self.verified_fingerprints}'.encode())
        digest.update(f'vptr-sanitizer:{self.vptr_sanitizer}'.encode())

    def configure(self, workspace: Workspace) -> None:
        CMakeRecipeMixin.configure(self, workspace)

        stp = self.find_stp(workspace)
        z3 = self.find_z3(workspace)
        llvm = self.find_llvm(workspace)
        klee_uclibc = self.find_klee_uclibc(workspace)
        klee_libcxx = self.find_klee_libcxx(workspace)

        self.cmake.set_flag('USE_CMAKE_FIND_PACKAGE_LLVM', True)
        self.cmake.set_flag('LLVM_DIR', llvm.paths["cmake_export_dir"])
        self.cmake.set_flag('LIT_TOOL', llvm.paths["llvm-lit"])
        self.cmake.set_flag('ENABLE_SOLVER_STP', True)
        self.cmake.set_flag('STP_DIR', stp.paths["src_dir"])
        self.cmake.set_flag('STP_STATIC_LIBRARY', stp.paths["libstp"])
        self.cmake.set_flag('ENABLE_SOLVER_Z3', True)
        self.cmake.set_flag('Z3_INCLUDE_DIRS', z3.paths["include_dir"])
        if z3.gmp:
            self.cmake.set_flag('Z3_LIBRARIES', f'{z3.paths["libz3"]};{z3.paths["libgmp"]}')
        else:
            self.cmake.set_flag('Z3_LIBRARIES', z3.paths["libz3"])
        self.cmake.set_flag('ENABLE_POSIX_RUNTIME', True)
        self.cmake.set_flag('ENABLE_KLEE_UCLIBC', True)
        self.cmake.set_flag('KLEE_UCLIBC_PATH', klee_uclibc.paths["build_dir"])

        self.cmake.set_flag('ENABLE_SYSTEM_TESTS', True)
        self.cmake.set_flag('ENABLE_UNIT_TESTS', True)

        if klee_libcxx:
            self.cmake.set_flag('ENABLE_KLEE_LIBCXX', True)
            self.cmake.set_flag('KLEE_LIBCXX_DIR', klee_libcxx.paths["build_dir"])
            self.cmake.set_flag('KLEE_LIBCXX_INCLUDE_DIR', klee_libcxx.paths["include_dir"])

        self.cmake.set_flag('VERIFIED_FINGERPRINTS', self.verified_fingerprints)

        if self.vptr_sanitizer:
            cxx_flags = self.profile["cxx_flags"].copy()
            cxx_flags.append("-fsanitize=vptr")
            self.cmake.set_extra_cxx_flags(cxx_flags)

    def add_to_env(self, env, workspace: Workspace):
        env_prepend_path(env, "PATH", self.paths["build_dir"] / "bin")
        env_prepend_path(env, "C_INCLUDE_PATH", self.paths["src_dir"] / "include")
        env_prepend_path(env, "C_INCLUDE_PATH", self.paths["src_dir"] / "include" / "klee" / "runtime")


register_recipe(PORSE)
