from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2s
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, cast

from workspace.build_systems import CMakeConfig
from workspace.util import env_prepend_path

from .all_recipes import register_recipe
from .recipe import Recipe

if TYPE_CHECKING:
    from workspace.workspace import Workspace


class Z3(Recipe):  # pylint: disable=invalid-name,too-many-instance-attributes
    """The z3 constraint solver"""

    default_name = "z3"
    profiles = {
        "release": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Release',
            },
            "c_flags": [],
            "cxx_flags": [],
        },
        "rel+debinfo": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'RelWithDebInfo',
            },
            "c_flags": ["-fno-omit-frame-pointer"],
            "cxx_flags": ["-fno-omit-frame-pointer"],
        },
        "debug": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Debug',
            },
            "c_flags": [],
            "cxx_flags": [],
        },
    }

    def __init__(  # pylint: disable=too-many-arguments
            self,
            profile,
            branch=None,
            repository="github://Z3Prover/z3.git",
            name=default_name,
            shared=True,
            openmp=True,
            cmake_adjustments=None):
        super().__init__(name)
        self.branch = branch
        self.profile = profile
        self.repository = repository
        self.shared = shared
        self.openmp = openmp
        self.cmake_adjustments = cmake_adjustments if cmake_adjustments is not None else []

        self.paths = None
        self.cmake = None

        assert self.profile in self.profiles, (
            f'[{self.__class__.__name__}] the recipe for {self.name} does not contain a profile "{self.profile}"!')

    def initialize(self, workspace: Workspace):
        def _compute_digest(self, workspace: Workspace):
            del workspace  # unused parameter

            digest = blake2s()
            digest.update(self.name.encode())
            digest.update(self.profile.encode())
            digest.update(f'shared:{self.shared}'.encode())
            digest.update(f'openmp:{self.openmp}'.encode())
            for adjustment in self.cmake_adjustments:
                digest.update("CMAKE_ADJUSTMENT:".encode())
                digest.update(adjustment.encode())

            # branch and repository need not be part of the digest, as we will build whatever
            # we find at the target path, no matter what it turns out to be at build time

            return digest.hexdigest()[:12]

        def _make_internal_paths(self, workspace: Workspace):
            @dataclass
            class InternalPaths:
                src_dir: Path
                build_dir: Path
                libz3: Path

            build_dir = workspace.build_dir / f'{self.name}-{self.profile}-{self.digest}'
            paths = InternalPaths(src_dir=workspace.ws_path / self.name,
                                  build_dir=build_dir,
                                  libz3=build_dir / "libz3.so" if self.shared else build_dir / "libz3.a")
            return paths

        self.digest = _compute_digest(self, workspace)
        self.paths = _make_internal_paths(self, workspace)
        self.repository = Recipe.concretize_repo_uri(self.repository, workspace)

        self.cmake = CMakeConfig(workspace)

    def setup(self, workspace: Workspace):
        if not self.paths.src_dir.is_dir():
            workspace.git_add_exclude_path(self.paths.src_dir)
            workspace.reference_clone(self.repository, target_path=self.paths.src_dir, branch=self.branch)
            workspace.apply_patches("z3", self.paths.src_dir)

    def _configure(self, workspace: Workspace):
        cxx_flags = cast(List[str], self.profiles[self.profile]["cxx_flags"])
        c_flags = cast(List[str], self.profiles[self.profile]["c_flags"])
        self.cmake.set_extra_c_flags(c_flags)
        self.cmake.set_extra_cxx_flags(cxx_flags)

        self.cmake.set_flag("BUILD_LIBZ3_SHARED", self.shared)
        self.cmake.set_flag("USE_OPENMP", self.openmp)

        for name, value in cast(Dict, self.profiles[self.profile]["cmake_args"]).items():
            self.cmake.set_flag(name, value)
        self.cmake.adjust_flags(self.cmake_adjustments)

        self.cmake.configure(workspace, self.paths.src_dir, self.paths.build_dir)

    def build(self, workspace: Workspace):
        if not self.cmake.is_configured(workspace, self.paths.src_dir, self.paths.build_dir):
            self._configure(workspace)
        self.cmake.build(workspace, self.paths.src_dir, self.paths.build_dir)

    def add_to_env(self, env, workspace: Workspace):
        env_prepend_path(env, "PATH", self.paths.build_dir)


register_recipe(Z3)
