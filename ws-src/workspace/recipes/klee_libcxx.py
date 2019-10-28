from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Union

from workspace.build_systems.cmake_recipe_mixin import CMakeRecipeMixin
from workspace.util import newer_than, run_with_prefix

from .all_recipes import register_recipe
from .klee_libcxxabi import KLEE_LIBCXXABI
from .llvm import LLVM
from .recipe import Recipe

if TYPE_CHECKING:
    import hashlib
    from workspace import Workspace


class KLEE_LIBCXX(Recipe, CMakeRecipeMixin):  # pylint: disable=invalid-name
    """LLVM's libcxx built for KLEE"""

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
            "c_flags": ["-fno-omit-frame-pointer", "-g3", "-fdebug-types-section"],
            "cxx_flags": ["-fno-omit-frame-pointer", "-g3", "-fdebug-types-section"],
            "is_performance_build": True,
            "has_debug_info": True,
        },
        "debug": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Debug',
                'LLVM_ENABLE_ASSERTIONS': True,
            },
            "c_flags": ["-fno-omit-frame-pointer", "-g3", "-fdebug-types-section"],
            "cxx_flags": ["-fno-omit-frame-pointer", "-g3", "-fdebug-types-section"],
            "is_performance_build": False,
            "has_debug_info": True,
        },
    }

    default_arguments: Dict[str, Any] = {
        "llvm": LLVM().default_name,
        "klee-libcxxabi": KLEE_LIBCXXABI().default_name,
    }

    argument_schema: Dict[str, Any] = {
        "llvm": str,
        "klee-libcxxabi": str,
    }

    def find_llvm(self, workspace: Workspace) -> LLVM:
        return self._find_previous_build(workspace, "llvm", LLVM)

    def find_klee_libcxxabi(self, workspace: Workspace) -> KLEE_LIBCXXABI:
        return self._find_previous_build(workspace, "klee-libcxxabi", KLEE_LIBCXXABI)

    def _get_wllvm_env(self, workspace: Workspace) -> Dict[str, str]:
        env = workspace.get_env()

        llvm = self.find_llvm(workspace)

        env['LLVM_COMPILER'] = "clang"
        env['LLVM_COMPILER_PATH'] = str(llvm.paths["bin_dir"])

        return env

    def __init__(self, **kwargs):
        CMakeRecipeMixin.__init__(self)
        Recipe.__init__(self, **kwargs)

    def setup(self, workspace: Workspace):
        klee_libcxxabi = self.find_klee_libcxxabi(workspace)
        assert klee_libcxxabi.paths["libcxx_src_dir"].exists(), "Could not find 'libcxx' sources"

    def initialize(self, workspace: Workspace):
        Recipe.initialize(self, workspace)
        CMakeRecipeMixin.initialize(self, workspace)

        klee_libcxxabi = self.find_klee_libcxxabi(workspace)

        self.paths["src_dir"] = klee_libcxxabi.paths["libcxx_src_dir"]
        self.paths["include_dir"] = self.paths["src_dir"] / "include"
        self.paths["lib_dir"] = self.paths["build_dir"] / "lib"
        self.paths["libcxx.so"] = self.paths["lib_dir"] / "libc++.so.1.0"
        self.paths["libcxx.bc"] = self.paths["lib_dir"] / "libc++.so.1.0.bc"
        self.paths["klee_libcxx.bc"] = self.paths["lib_dir"] / "libc++.so.bc"

        CMakeRecipeMixin.set_build_env(self, self._get_wllvm_env(workspace))
        CMakeRecipeMixin.set_use_ccache(self, False)
        CMakeRecipeMixin.set_build_targets(self, ["cxx"])

    def _compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        Recipe.compute_digest(self, workspace, digest)
        CMakeRecipeMixin.compute_digest(self, workspace, digest)

        digest.update(self.find_llvm(workspace).digest)
        digest.update(self.find_klee_libcxxabi(workspace).digest)

    def configure(self, workspace: Workspace) -> None:
        llvm = self.find_llvm(workspace)
        klee_libcxxabi = self.find_klee_libcxxabi(workspace)

        self.cmake.set_flag('CMAKE_C_COMPILER', 'wllvm')
        self.cmake.set_flag('CMAKE_CXX_COMPILER', 'wllvm++')
        self.cmake.set_flag('LLVM_CONFIG_PATH', llvm.paths["llvm-config"])

        self.cmake.set_flag('LIBCXX_CXX_ABI', 'libcxxabi')
        self.cmake.set_flag('LIBCXX_CXX_ABI_INCLUDE_PATHS', klee_libcxxabi.paths["include_dir"])
        self.cmake.set_flag('LIBCXX_CXX_ABI_LIBRARY_PATH', klee_libcxxabi.paths["lib_dir"])
        self.cmake.set_flag('LIBCXX_ENABLE_ABI_LINKER_SCRIPT', False)
        self.cmake.set_flag('LIBCXX_ENABLE_SHARED', True)
        self.cmake.set_flag('LIBCXX_INCLUDE_BENCHMARKS', False)
        self.cmake.set_flag('LIBCXX_ENABLE_THREADS', False)

        config_env: Dict[str, str] = dict(CMakeRecipeMixin.get_build_env(self))
        config_env["WLLVM_CONFIGURE_ONLY"] = "ON"
        CMakeRecipeMixin.set_configure_env(self, config_env)

    def build(self, workspace: Workspace):
        klee_libcxxabi = self.find_klee_libcxxabi(workspace)

        CMakeRecipeMixin.build(self, workspace)

        if not newer_than(target=self.paths["libcxx.bc"], others=[self.paths["libcxx.so"]]):
            llvm = self.find_llvm(workspace)
            extract_bc_cmd: List[Union[str, Path]] = [
                "extract-bc", "--linker", llvm.paths["llvm-link"], "--archiver", llvm.paths["llvm-ar"], "-o",
                self.paths["libcxx.bc"], self.paths["libcxx.so"]
            ]
            run_with_prefix(extract_bc_cmd, self.output_prefix, check=True, cwd=self.paths["build_dir"])

        if not newer_than(target=self.paths["klee_libcxx.bc"],
                          others=[self.paths["libcxx.bc"], klee_libcxxabi.paths["libcxxabi.bc"]]):
            link_cmd: List[Union[str, Path]] = [
                llvm.paths["llvm-link"], "-o", self.paths["klee_libcxx.bc"], self.paths["libcxx.bc"],
                klee_libcxxabi.paths["libcxxabi.bc"]
            ]
            run_with_prefix(link_cmd, self.output_prefix, check=True, cwd=self.paths["build_dir"])

    def add_to_env(self, env, workspace: Workspace):
        pass


register_recipe(KLEE_LIBCXX)
