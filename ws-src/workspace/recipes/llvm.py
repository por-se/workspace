import os, shutil, psutil
from dataclasses import dataclass
from hashlib import blake2s
from typing import Dict, List, Optional, cast

from workspace.workspace import Workspace, _run
from workspace.build_systems import CMakeConfig, Linker
from workspace.util import j_from_num_threads, env_prepend_path
from . import Recipe

from pathlib import Path


class LLVM(Recipe):
    default_name = "llvm"
    profiles = {
        "release": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Release',
                'LLVM_ENABLE_ASSERTIONS': True,
            },
            "c_flags": [],
            "cxx_flags": [],
            "is_performance_build": True,
            "has_debug_info": False,
        },
        "rel+debinfo": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'RelWithDebInfo',
                'LLVM_ENABLE_ASSERTIONS': True,
            },
            "c_flags": ["-fno-omit-frame-pointer"],
            "cxx_flags": ["-fno-omit-frame-pointer"],
            "is_performance_build": True,
            "has_debug_info": True,
        },
        "debug": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Debug',
                'LLVM_ENABLE_ASSERTIONS': True,
            },
            "c_flags": [],
            "cxx_flags": [],
            "is_performance_build": False,
            "has_debug_info": True,
        },
    }


    def __init__(self,
                 profile,
                 branch=None,
                 repository="github://llvm/llvm-project.git",
                 name=default_name,
                 cmake_adjustments=[]):
        """Build LLVM."""
        super().__init__(name)
        self.branch = branch
        self.profile = profile
        self.repository = repository
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

            return digest.hexdigest()[:12]

        def _make_internal_paths(self, ws: Workspace):
            @dataclass
            class InternalPaths:
                src_dir: Path
                build_dir: Path
                tablegen: Optional[Path] = None

            paths = InternalPaths(
                src_dir=ws.ws_path / self.name,
                build_dir=ws.build_dir / f'{self.name}-{self.profile}-{self.digest}'
            )
            paths.tablegen = paths.build_dir / 'bin/llvm-tblgen'
            return paths

        if self.profile != "release":
            self._release_build = LLVM(profile = "release",
                                       branch = self.branch,
                                       repository = self.repository,
                                       name = self.name,
                                       cmake_adjustments = [])
            self._release_build.initialize(ws)

        self.digest = _compute_digest(self, ws)
        self.paths = _make_internal_paths(self, ws)
        self.repository = Recipe.concretize_repo_uri(self.repository, ws)

        self.cmake = CMakeConfig(ws)

    def setup(self, ws: Workspace):
        if self.profile != "release":
            self._release_build.setup(ws)

        if not self.paths.src_dir.is_dir():
            ws.git_add_exclude_path(self.paths.src_dir)
            ws.reference_clone(
                self.repository,
                target_path=self.paths.src_dir,
                branch=self.branch,
                sparse=["/llvm", "/clang"])
            ws.apply_patches("llvm", self.paths.src_dir)

    def _configure(self, ws: Workspace):
        cxx_flags = cast(List[str], self.profiles[self.profile]["cxx_flags"])
        c_flags = cast(List[str], self.profiles[self.profile]["c_flags"])
        self.cmake.set_extra_c_flags(c_flags)
        self.cmake.set_extra_cxx_flags(cxx_flags)

        self.cmake.set_flag("LLVM_EXTERNAL_CLANG_SOURCE_DIR", str(self.paths.src_dir / "clang"))
        self.cmake.set_flag("LLVM_TARGETS_TO_BUILD", "X86")
        self.cmake.set_flag("LLVM_INCLUDE_EXAMPLES", False)
        self.cmake.set_flag("HAVE_VALGRIND_VALGRIND_H", False)

        if not self.profiles[self.profile]["is_performance_build"]:
            self.cmake.set_flag("LLVM_TABLEGEN", str(self._release_build.paths.tablegen))

        avail_mem = psutil.virtual_memory().available
        if self.profiles[self.profile]["has_debug_info"] and  avail_mem < ws.args.num_threads * 12000000000 and avail_mem < 35000000000:
            print(
                f"[{self.__class__.__name__}] less than 12G memory per thread (or 35G total) available during a build containing debug information; restricting link-parallelism to 1 [-DLLVM_PARALLEL_LINK_JOBS=1]"
            )
            self.cmake.set_flag("LLVM_PARALLEL_LINK_JOBS", 1)

        for name, value in cast(Dict, self.profiles[self.profile]["cmake_args"]).items():
            self.cmake.set_flag(name, value)
        self.cmake.adjust_flags(self.cmake_adjustments)

        self.cmake.configure(ws, self.paths.src_dir / "llvm", self.paths.build_dir)

    def build(self, ws: Workspace, target=None):
        if self.profile != "release":
            self._release_build.build(ws, target='bin/llvm-tblgen')

        if not self.cmake.is_configured(ws, self.paths.src_dir / "llvm", self.paths.build_dir):
            self._configure(ws)
        self.cmake.build(ws, self.paths.src_dir / "llvm", self.paths.build_dir, target=target)

    def clean(self, ws: Workspace):
        if ws.args.dist_clean:
            if self.paths.src_dir.is_dir():
                shutil.rmtree(self.paths.src_dir)
            ws.git_remove_exclude_path(self.paths.src_dir)

    def add_to_env(self, env, ws: Workspace):
        env_prepend_path(env, "PATH", self.paths.build_dir / "bin")
