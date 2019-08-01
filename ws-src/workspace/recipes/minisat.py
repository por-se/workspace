from dataclasses import dataclass
from hashlib import blake2s
from pathlib import Path
import shutil

from workspace.workspace import Workspace
from workspace.build_systems import CMakeConfig
from workspace.util import env_prepend_path
from . import Recipe


class MINISAT(Recipe):  # pylint: disable=invalid-name,too-many-instance-attributes
    default_name = "minisat"

    def __init__(  # pylint: disable=too-many-arguments
            self,
            branch=None,
            name=default_name,
            repository="github://stp/minisat.git",
            cmake_adjustments=[]):
        super().__init__(name)
        self.branch = branch
        self.repository = repository
        self.cmake_adjustments = cmake_adjustments

        self.cmake = None
        self.paths = None

    def initialize(self, workspace: Workspace):
        def _compute_digest(self, workspace: Workspace):
            del workspace  # unused parameter

            digest = blake2s()
            digest.update(self.name.encode())
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

            paths = InternalPaths(src_dir=workspace.ws_path / self.name,
                                  build_dir=workspace.build_dir / f'{self.name}-{self.digest}')
            return paths

        self.digest = _compute_digest(self, workspace)
        self.paths = _make_internal_paths(self, workspace)
        self.repository = Recipe.concretize_repo_uri(self.repository, workspace)

        self.cmake = CMakeConfig(workspace)

    def setup(self, workspace: Workspace):
        if not self.paths.src_dir.is_dir():
            workspace.git_add_exclude_path(self.paths.src_dir)
            workspace.reference_clone(self.repository, target_path=self.paths.src_dir, branch=self.branch)
            workspace.apply_patches("minisat", self.paths.src_dir)

    def _configure(self, workspace: Workspace):
        self.cmake.set_extra_cxx_flags(["-std=c++11"])
        self.cmake.adjust_flags(self.cmake_adjustments)

        self.cmake.configure(workspace, self.paths.src_dir, self.paths.build_dir)

    def build(self, workspace: Workspace):
        if not self.cmake.is_configured(workspace, self.paths.src_dir, self.paths.build_dir):
            self._configure(workspace)
        self.cmake.build(workspace, self.paths.src_dir, self.paths.build_dir)

    def clean(self, workspace: Workspace):
        if workspace.args.dist_clean:
            if self.paths.src_dir.is_dir():
                shutil.rmtree(self.paths.src_dir)
            workspace.git_remove_exclude_path(self.paths.src_dir)

    def add_to_env(self, env, workspace: Workspace):
        env_prepend_path(env, "PATH", self.paths.build_dir)
