from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from workspace.build_systems.cmake_recipe_mixin import CMakeRecipeMixin
from workspace.util import env_prepend_path
from workspace.vcs.git import GitRecipeMixin

from .all_recipes import register_recipe
from .klee_uclibc import KLEE_UCLIBC
from .llvm import LLVM
from .pseudoalloc import PSEUDOALLOC
from .recipe import Recipe
from .simulator import SIMULATOR
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
        "simulator": SIMULATOR().default_name,
        "pseudoalloc": PSEUDOALLOC().default_name,
    }

    argument_schema: Dict[str, Any] = {
        "klee-uclibc": str,
        "llvm": str,
        "z3": str,
        "stp": str,
        "simulator": str,
        "pseudoalloc": str,
    }

    def find_klee_uclibc(self, workspace: Workspace) -> KLEE_UCLIBC:
        return self._find_previous_build(workspace, "klee-uclibc", KLEE_UCLIBC)

    def find_llvm(self, workspace: Workspace) -> LLVM:
        return self._find_previous_build(workspace, "llvm", LLVM)

    def find_z3(self, workspace: Workspace) -> Z3:
        return self._find_previous_build(workspace, "z3", Z3)

    def find_stp(self, workspace: Workspace) -> STP:
        return self._find_previous_build(workspace, "stp", STP)

    def find_simulator(self, workspace: Workspace) -> SIMULATOR:
        return self._find_previous_build(workspace, "simulator", SIMULATOR)

    def find_pseudoalloc(self, workspace: Workspace) -> PSEUDOALLOC:
        return self._find_previous_build(workspace, "pseudoalloc", PSEUDOALLOC)

    def __init__(self, **kwargs):
        GitRecipeMixin.__init__(self,
                                "laboratory://symbiosys/projects/concurrent-symbolic-execution/klee.git",
                                upstream="github://klee/klee.git")
        CMakeRecipeMixin.__init__(self)
        Recipe.__init__(self, **kwargs)

    def initialize(self, workspace: Workspace) -> None:
        Recipe.initialize(self, workspace)
        CMakeRecipeMixin.initialize(self, workspace)

    def compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        Recipe.compute_digest(self, workspace, digest)
        CMakeRecipeMixin.compute_digest(self, workspace, digest)

        digest.update(self.find_stp(workspace).digest)
        digest.update(self.find_z3(workspace).digest)
        digest.update(self.find_llvm(workspace).digest)
        digest.update(self.find_klee_uclibc(workspace).digest)
        digest.update(self.find_pseudoalloc(workspace).digest)
        digest.update(self.find_simulator(workspace).digest)

    def configure(self, workspace: Workspace):
        llvm = self.find_llvm(workspace)
        if self.profile_name == "sanitized" and llvm.rtti:
            self.profile["cxx_flags"].append("-fsanitize=vptr")
        elif self.profile_name == "sanitized":
            print(f'[{self.__class__.__name__}] LLVM built without RTTI, vptr sanitizer (of UBSan) cannot be enabled.')

        CMakeRecipeMixin.configure(self, workspace)

        stp = self.find_stp(workspace)
        z3 = self.find_z3(workspace)
        klee_uclibc = self.find_klee_uclibc(workspace)
        pseudoalloc = self.find_pseudoalloc(workspace)
        simulator = self.find_simulator(workspace)

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
        self.cmake.set_flag('ENABLE_PTHREAD_RUNTIME', True)
        self.cmake.set_flag('ENABLE_KLEE_UCLIBC', True)
        self.cmake.set_flag('KLEE_UCLIBC_PATH', klee_uclibc.paths["build_dir"])
        self.cmake.set_flag('PSEUDOALLOC_DIR', pseudoalloc.paths["build_dir"])
        self.cmake.set_flag('POR_SIMULATOR_DIR', simulator.paths["build_dir"])

        self.cmake.set_flag('ENABLE_SYSTEM_TESTS', True)
        self.cmake.set_flag('ENABLE_UNIT_TESTS', True)

    def add_to_env(self, env, workspace: Workspace):
        env_prepend_path(env, "PATH", self.paths["build_dir"] / "bin")
        env_prepend_path(env, "C_INCLUDE_PATH", self.paths["src_dir"] / "include")
        env_prepend_path(env, "C_INCLUDE_PATH", self.paths["src_dir"] / "include" / "klee" / "runtime")


register_recipe(PORSE)
