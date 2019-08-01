import os, shutil
from dataclasses import dataclass
from hashlib import blake2s
from typing import cast, List, Dict

from workspace.workspace import Workspace, _run
from workspace.build_systems import CMakeConfig, Linker
from workspace.util import j_from_num_threads, env_prepend_path
from . import Recipe

from pathlib import Path


class MINISAT(Recipe):
    default_name = "minisat"

    def __init__(self, branch=None, name=default_name, repository="github://stp/minisat.git", cmake_adjustments=[]):
        super().__init__(name)
        self.branch = branch
        self.repository = repository
        self.cmake_adjustments = cmake_adjustments

    def initialize(self, ws: Workspace):
        def _compute_digest(self, ws: Workspace):
            digest = blake2s()
            digest.update(self.name.encode())
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

            paths = InternalPaths(src_dir=ws.ws_path / self.name, build_dir=ws.build_dir / f'{self.name}-{self.digest}')
            return paths

        self.digest = _compute_digest(self, ws)
        self.paths = _make_internal_paths(self, ws)
        self.repository = Recipe.concretize_repo_uri(self.repository, ws)

        self.cmake = CMakeConfig(ws)

    def setup(self, ws: Workspace):
        if not self.paths.src_dir.is_dir():
            ws.git_add_exclude_path(self.paths.src_dir)
            ws.reference_clone(self.repository, target_path=self.paths.src_dir, branch=self.branch)
            ws.apply_patches("minisat", self.paths.src_dir)

    def _configure(self, ws: Workspace):
        self.cmake.set_extra_cxx_flags(["-std=c++11"])
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
