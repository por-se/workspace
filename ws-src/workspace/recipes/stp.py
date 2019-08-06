from dataclasses import dataclass
from hashlib import blake2s
from pathlib import Path
import sys
from typing import cast, List, Dict

from workspace.workspace import Workspace
from workspace.build_systems import CMakeConfig, Linker
from workspace.util import env_prepend_path
from . import Recipe, MINISAT


class STP(Recipe):  # pylint: disable=invalid-name,too-many-instance-attributes
    default_name = "stp"
    profiles = {
        "release": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Release',
                'ENABLE_ASSERTIONS': True,
                'SANITIZE': False,
            },
            "c_flags": [],
            "cxx_flags": [],
        },
        "rel+debinfo": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'RelWithDebInfo',
                'ENABLE_ASSERTIONS': True,
                'SANITIZE': False,
            },
            "c_flags": ["-fno-omit-frame-pointer"],
            "cxx_flags": ["-fno-omit-frame-pointer"],
        },
        "debug": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Debug',
                'ENABLE_ASSERTIONS': True,
                'SANITIZE': False,
            },
            "c_flags": [],
            "cxx_flags": [],
        },
    }

    def __init__(  # pylint: disable=too-many-arguments
            self,
            profile,
            branch=None,
            name=default_name,
            repository="github://stp/stp.git",
            minisat_name=MINISAT.default_name,
            cmake_adjustments=[]):
        super().__init__(name)
        self.branch = branch
        self.profile = profile
        self.repository = repository
        self.minisat_name = minisat_name
        self.cmake_adjustments = cmake_adjustments

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

            minisat = workspace.find_build(build_name=self.minisat_name, before=self)
            assert minisat, "STP requires minisat"
            digest.update(minisat.digest.encode())

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
        if self.cmake.linker == Linker.LLD:
            msg = ("warning: linking STP with lld may cause crashes, falling back to gold.\n"
                   "         see https://laboratory.comsys.rwth-aachen.de/symbiosys/projects/workspace_base/issues/34")
            print(msg, file=sys.stderr)
            self.cmake.linker = Linker.GOLD

    def setup(self, workspace: Workspace):
        if not self.paths.src_dir.is_dir():
            workspace.git_add_exclude_path(self.paths.src_dir)
            workspace.reference_clone(self.repository, target_path=self.paths.src_dir, branch=self.branch)
            workspace.apply_patches("stp", self.paths.src_dir)

    def _configure(self, workspace: Workspace):
        cxx_flags = cast(List[str], self.profiles[self.profile]["cxx_flags"])
        c_flags = cast(List[str], self.profiles[self.profile]["c_flags"])
        self.cmake.set_extra_c_flags(c_flags)
        self.cmake.set_extra_cxx_flags(cxx_flags)

        minisat = workspace.find_build(build_name=self.minisat_name, before=self)
        assert minisat, "STP requires minisat"
        self.cmake.set_flag("MINISAT_LIBRARY", f"{minisat.paths.build_dir}/libminisat.a")
        self.cmake.set_flag("MINISAT_INCLUDE_DIR", str(minisat.paths.src_dir))

        self.cmake.set_flag("NOCRYPTOMINISAT", True)
        self.cmake.set_flag("STATICCOMPILE", True)
        self.cmake.set_flag("BUILD_SHARED_LIBS", False)
        self.cmake.set_flag("ENABLE_PYTHON_INTERFACE", False)

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
