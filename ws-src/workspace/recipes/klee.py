from __future__ import annotations
from dataclasses import dataclass
from hashlib import blake2s
from pathlib import Path
import shutil
from typing import TYPE_CHECKING, cast, List, Dict

from workspace.build_systems import CMakeConfig
from workspace.util import env_prepend_path
from .all_recipes import register_recipe
from .recipe import Recipe
from .llvm import LLVM
from .z3 import Z3
from .stp import STP
from .klee_uclibc import KLEE_UCLIBC
if TYPE_CHECKING:
    from workspace.workspace import Workspace


class KLEE(Recipe):  # pylint: disable=invalid-name,too-many-instance-attributes
    default_name = "klee"
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

    def __init__(  # pylint: disable=too-many-arguments
            self,
            profile,
            branch=None,
            name=default_name,
            repository="github://klee/klee.git",
            stp_name=STP.default_name,
            z3_name=Z3.default_name,
            llvm_name=LLVM.default_name,
            klee_uclibc_name=KLEE_UCLIBC.default_name,
            cmake_adjustments=None):

        super().__init__(name)
        self.branch = branch
        self.profile = profile
        self.repository = repository
        self.stp_name = stp_name
        self.z3_name = z3_name
        self.llvm_name = llvm_name
        self.klee_uclibc_name = klee_uclibc_name
        self.cmake_adjustments = cmake_adjustments if cmake_adjustments is not None else []

        self.cmake = None
        self.paths = None

        assert self.profile in self.profiles, f'[{self.__class__.__name__}] the recipe for {self.name} does not contain a profile "{self.profile}"!'

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

            stp = workspace.find_build(build_name=self.stp_name, before=self)
            z3 = workspace.find_build(build_name=self.z3_name, before=self)
            llvm = workspace.find_build(build_name=self.llvm_name, before=self)
            klee_uclibc = workspace.find_build(build_name=self.klee_uclibc_name, before=self)

            assert stp, "klee requires stp"
            assert z3, "klee requires z3"
            assert llvm, "klee requires llvm"
            assert klee_uclibc, "klee requires klee_uclibc"

            digest.update(stp.digest.encode())
            digest.update(z3.digest.encode())
            digest.update(llvm.digest.encode())
            digest.update(klee_uclibc.digest.encode())

            return digest.hexdigest()[:12]

        def _make_internal_paths(self, workspace: Workspace):
            @dataclass
            class InternalPaths:
                src_dir: Path
                build_dir: Path

            paths = InternalPaths(src_dir=workspace.ws_path / self.name,
                                  build_dir=workspace.build_dir / f'{self.name}-{self.profile}-{self.digest}')
            return paths

        self.digest = _compute_digest(self, workspace)
        self.paths = _make_internal_paths(self, workspace)
        self.repository = Recipe.concretize_repo_uri(self.repository, workspace)

        self.cmake = CMakeConfig(workspace)

    def setup(self, workspace: Workspace):
        if not self.paths.src_dir.is_dir():
            workspace.git_add_exclude_path(self.paths.src_dir)
            workspace.reference_clone(self.repository, target_path=self.paths.src_dir, branch=self.branch)
            workspace.apply_patches("klee", self.paths.src_dir)

    def _configure(self, workspace: Workspace):
        cxx_flags = cast(List[str], self.profiles[self.profile]["cxx_flags"])
        c_flags = cast(List[str], self.profiles[self.profile]["c_flags"])
        self.cmake.set_extra_c_flags(c_flags)
        self.cmake.set_extra_cxx_flags(cxx_flags)

        stp = workspace.find_build(build_name=self.stp_name, before=self)
        z3 = workspace.find_build(build_name=self.z3_name, before=self)
        llvm = workspace.find_build(build_name=self.llvm_name, before=self)
        klee_uclibc = workspace.find_build(build_name=self.klee_uclibc_name, before=self)

        assert stp, "klee requires stp"
        assert z3, "klee requires z3"
        assert llvm, "klee requires llvm"
        assert klee_uclibc, "klee requires klee_uclibc"

        self.cmake.set_flag('USE_CMAKE_FIND_PACKAGE_LLVM', True)
        self.cmake.set_flag('LLVM_DIR', str(llvm.paths.build_dir / "lib/cmake/llvm/"))
        self.cmake.set_flag('ENABLE_SOLVER_STP', True)
        self.cmake.set_flag('STP_DIR', str(stp.paths.src_dir))
        self.cmake.set_flag('STP_STATIC_LIBRARY', str(stp.paths.build_dir / "lib/libstp.a"))
        self.cmake.set_flag('ENABLE_SOLVER_Z3', True)
        self.cmake.set_flag('Z3_INCLUDE_DIRS', str(z3.paths.src_dir / "src/api/"))
        self.cmake.set_flag('Z3_LIBRARIES', str(z3.paths.build_dir / "libz3.a"))
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
