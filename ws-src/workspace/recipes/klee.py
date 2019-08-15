from __future__ import annotations

import shutil
from dataclasses import dataclass
from hashlib import blake2s
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, cast

import schema

from workspace.build_systems import CMakeConfig
from workspace.settings import settings
from workspace.util import env_prepend_path
from workspace.vcs import git

from .all_recipes import register_recipe
from .klee_uclibc import KLEE_UCLIBC
from .llvm import LLVM
from .recipe import Recipe
from .stp import STP
from .z3 import Z3

if TYPE_CHECKING:
    from workspace import Workspace


class KLEE(Recipe):  # pylint: disable=invalid-name
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
        "name": "klee",
        "repository": "github://klee/klee.git",
        "branch": None,
        "klee-uclibc": KLEE_UCLIBC.default_arguments["name"],
        "llvm": LLVM.default_arguments["name"],
        "z3": Z3.default_arguments["name"],
        "stp": STP.default_arguments["name"],
        "cmake-adjustments": [],
    }

    argument_schema: Dict[str, Any] = {
        "name": str,
        "repository": str,
        "branch": schema.Or(str, None),
        "profile": schema.Or(*profiles.keys()),
        "klee-uclibc": str,
        "llvm": str,
        "z3": str,
        "stp": str,
        "cmake-adjustments": [str],
    }

    @property
    def branch(self) -> str:
        return self.arguments["branch"]

    @property
    def profile(self) -> str:
        return self.arguments["profile"]

    @property
    def cmake_adjustments(self) -> List[str]:
        return self.arguments["cmake-adjustments"]

    def find_klee_uclibc(self, workspace: Workspace) -> KLEE_UCLIBC:
        return self._find_previous_build(workspace, "klee-uclibc", KLEE_UCLIBC)

    def find_llvm(self, workspace: Workspace) -> LLVM:
        return self._find_previous_build(workspace, "llvm", LLVM)

    def find_z3(self, workspace: Workspace) -> Z3:
        return self._find_previous_build(workspace, "z3", Z3)

    def find_stp(self, workspace: Workspace) -> STP:
        return self._find_previous_build(workspace, "stp", STP)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cmake = None
        self.paths = None
        self.repository = None

    def initialize(self, workspace: Workspace):
        def _compute_digest(self, workspace: Workspace):
            digest = blake2s()
            digest.update(self.name.encode())
            digest.update(self.profile.encode())
            for adjustment in self.cmake_adjustments:
                digest.update("CMAKE_ADJUSTMENT:".encode())
                digest.update(adjustment.encode())

            # branch and repository need not be part of the digest, as we will build whatever
            # we find at the target path, no matter what it turns out to be at build time

            digest.update(self.find_stp(workspace).digest.encode())
            digest.update(self.find_z3(workspace).digest.encode())
            digest.update(self.find_llvm(workspace).digest.encode())
            digest.update(self.find_klee_uclibc(workspace).digest.encode())

            return digest.hexdigest()[:12]

        def _make_internal_paths(self, workspace: Workspace):
            @dataclass
            class InternalPaths:
                src_dir: Path
                build_dir: Path

            paths = InternalPaths(src_dir=settings.ws_path / self.name,
                                  build_dir=workspace.build_dir / f'{self.name}-{self.profile}-{self.digest}')
            return paths

        self.digest = _compute_digest(self, workspace)
        self.paths = _make_internal_paths(self, workspace)
        self.repository = Recipe.concretize_repo_uri(self.arguments["repository"], workspace)

        self.cmake = CMakeConfig(workspace)

    def setup(self, workspace: Workspace):
        if not self.paths.src_dir.is_dir():
            git.add_exclude_path(self.paths.src_dir)
            git.reference_clone(self.repository, target_path=self.paths.src_dir, branch=self.branch)
            git.apply_patches(workspace.patch_dir, "klee", self.paths.src_dir)

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
