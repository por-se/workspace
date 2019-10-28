from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Union

from workspace.build_systems.cmake_recipe_mixin import CMakeRecipeMixin
from workspace.util import newer_than, run_with_prefix
from workspace.vcs.git import GitRecipeMixin

from .all_recipes import register_recipe
from .llvm import LLVM
from .recipe import Recipe

if TYPE_CHECKING:
    import hashlib
    from workspace import Workspace


class KLEE_LIBCXXABI(Recipe, GitRecipeMixin, CMakeRecipeMixin):  # pylint: disable=invalid-name
    """LLVM's libcxxabi built for KLEE"""

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
    }

    argument_schema: Dict[str, Any] = {
        "llvm": str,
    }

    def find_llvm(self, workspace: Workspace) -> LLVM:
        return self._find_previous_build(workspace, "llvm", LLVM)

    def __init__(self, **kwargs):
        GitRecipeMixin.__init__(self, "github://llvm/llvm-project.git", sparse=["/libcxx", "/libcxxabi"])
        CMakeRecipeMixin.__init__(self)
        Recipe.__init__(self, **kwargs)

    def _get_wllvm_env(self, workspace: Workspace) -> Dict[str, str]:
        env = workspace.get_env()

        llvm = self.find_llvm(workspace)

        env['LLVM_COMPILER'] = "clang"
        env['LLVM_COMPILER_PATH'] = str(llvm.paths["bin_dir"])

        return env

    def initialize(self, workspace: Workspace):
        Recipe.initialize(self, workspace)
        CMakeRecipeMixin.initialize(self, workspace)

        self.paths["libcxx_src_dir"] = self.paths["src_dir"] / "libcxx"
        self.paths["libcxxabi_src_dir"] = self.paths["src_dir"] / "libcxxabi"
        self.paths["cmake_src_dir"] = self.paths["libcxxabi_src_dir"]
        self.paths["lib_dir"] = self.paths["build_dir"] / "lib"
        self.paths["include_dir"] = self.paths["libcxxabi_src_dir"] / "include"
        self.paths["libcxxabi.so"] = self.paths["lib_dir"] / "libc++abi.so.1.0"
        self.paths["libcxxabi.bc"] = self.paths["lib_dir"] / "libc++abi.so.1.0.bc"

        CMakeRecipeMixin.set_build_env(self, self._get_wllvm_env(workspace))
        CMakeRecipeMixin.set_use_ccache(self, False)
        CMakeRecipeMixin.set_build_targets(self, ["cxxabi"])

    def _compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        Recipe.compute_digest(self, workspace, digest)
        CMakeRecipeMixin.compute_digest(self, workspace, digest)

        digest.update(self.find_llvm(workspace).digest)

    def configure(self, workspace: Workspace) -> None:
        CMakeRecipeMixin.configure(self, workspace)

        llvm = self.find_llvm(workspace)

        self.cmake.set_flag('CMAKE_C_COMPILER', 'wllvm')
        self.cmake.set_flag('CMAKE_CXX_COMPILER', 'wllvm++')
        self.cmake.set_flag('LLVM_CONFIG_PATH', llvm.paths["llvm-config"])

        self.cmake.set_flag('LIBCXXABI_LIBCXX_PATH', self.paths["libcxx_src_dir"])
        self.cmake.set_flag('LIBCXXABI_ENABLE_THREADS', False)

        config_env: Dict[str, str] = dict(CMakeRecipeMixin.get_build_env(self))
        config_env["WLLVM_CONFIGURE_ONLY"] = "ON"
        CMakeRecipeMixin.set_configure_env(self, config_env)

    def build(self, workspace: Workspace):
        CMakeRecipeMixin.build(self, workspace)

        if not newer_than(target=self.paths["libcxxabi.bc"], others=[self.paths["libcxxabi.so"]]):
            llvm = self.find_llvm(workspace)
            extract_bc_cmd: List[Union[str, Path]] = [
                "extract-bc", "--linker", llvm.paths["llvm-link"], "--archiver", llvm.paths["llvm-ar"], "-o",
                self.paths["libcxxabi.bc"], self.paths["libcxxabi.so"]
            ]
            run_with_prefix(extract_bc_cmd, self.output_prefix, check=True, cwd=self.paths["build_dir"])

    def add_to_env(self, env, workspace: Workspace):
        pass


register_recipe(KLEE_LIBCXXABI)
