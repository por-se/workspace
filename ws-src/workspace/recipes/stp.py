import os, shutil
from dataclasses import dataclass
from hashlib import blake2s
from typing import cast, List, Dict

from workspace.workspace import Workspace, _run
from workspace.build_systems import CMakeConfig, Linker
from workspace.util import j_from_num_threads, env_prepend_path
from . import Recipe, MINISAT

from pathlib import Path


class STP(Recipe):
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

    def __init__(self,
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

        assert self.profile in self.profiles, f'[{self.__class__.__name__}] the recipe for {self.name} does not contain a profile "{self.profile}"!'

    def initialize(self, ws: Workspace):
        def _compute_digest(self, ws: Workspace):
            digest = blake2s()
            digest.update(self.name.encode())
            digest.update(self.profile.encode())
            for adjustment in self.cmake_adjustments:
                digest.update("CMAKE_ADJUSTMENT:".encode())
                digest.update(adjustment.encode())

            # branch and repository need not be part of the digest, as we will build whatever
            # we find at the target path, no matter what it turns out to be at build time

            minisat = ws.find_build(build_name=self.minisat_name, before=self)
            assert minisat, "STP requires minisat"
            digest.update(minisat.digest.encode())

            return digest.hexdigest()[:12]

        def _make_internal_paths(self, ws: Workspace):
            @dataclass
            class InternalPaths:
                src_dir: Path
                build_dir: Path

            paths = InternalPaths(
                src_dir=ws.ws_path / self.name,
                build_dir=ws.build_dir / f'{self.name}-{self.profile}-{self.digest}'
            )
            return paths

        self.digest = _compute_digest(self, ws)
        self.paths = _make_internal_paths(self, ws)
        self.repository = Recipe.concretize_repo_uri(self.repository, ws)

        self.cmake = CMakeConfig(ws)
        # STP may crash when linked with LLD right now, see:
        # https://laboratory.comsys.rwth-aachen.de/symbiosys/projects/workspace_base/issues/34
        self.cmake.use_linker(Linker.GOLD)

    def setup(self, ws: Workspace):
        src_dir = self.paths.src_dir
        if not src_dir.is_dir():
            ws.git_add_exclude_path(src_dir)
            ws.reference_clone(
                self.repository,
                target_path=src_dir,
                branch=self.branch)
            ws.apply_patches("stp", src_dir)

    def _configure(self, ws: Workspace):
        cxx_flags = cast(List[str], self.profiles[self.profile]["cxx_flags"])
        c_flags = cast(List[str], self.profiles[self.profile]["c_flags"])
        self.cmake.set_extra_c_flags(c_flags)
        self.cmake.set_extra_cxx_flags(cxx_flags)

        minisat = ws.find_build(build_name=self.minisat_name, before=self)
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

        self.cmake.configure(ws, self.paths.src_dir, self.paths.build_dir)

    def build(self, ws: Workspace):
        if not self.cmake.is_configured(ws, self.paths.src_dir, self.paths.build_dir):
            self._configure(ws)
        self.cmake.build(ws, self.paths.src_dir, self.paths.build_dir)

    def clean(self, ws: Workspace):
        if ws.args.dist_clean:
            if self.paths.src_dir.is_dir():
                shutil.rmtree(self.paths.src_dir)
            ws.git_remove_exclude_path(self.paths.src_dir)

    def add_to_env(self, env, ws: Workspace):
        env_prepend_path(env, "PATH", self.paths.build_dir)
