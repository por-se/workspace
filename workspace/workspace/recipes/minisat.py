import os, multiprocessing, shutil
from hashlib import blake2s

from workspace.workspace import Workspace, _run
from workspace.util import j_from_num_threads, adjusted_cmake_args
from . import Recipe
from .llvm import LLVM

from pathlib import Path


class MINISAT(Recipe):
    default_name = "minisat"

    def __init__(self, branch, name=default_name, repository="git@github.com:stp/minisat.git", cmake_adjustments=[]):
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
            class InternalPaths:
                pass

            res = InternalPaths()
            res.local_repo_path = ws.ws_path / self.name
            res.build_path = ws.build_dir / f'{self.name}-{self.digest}'
            return res

        self.digest = _compute_digest(self, ws)
        self.paths = _make_internal_paths(self, ws)

    def setup(self, ws: Workspace):
        local_repo_path = self.paths.local_repo_path
        if not local_repo_path.is_dir():
            ws.git_add_exclude_path(local_repo_path)
            ws.reference_clone(
                self.repository,
                target_path=local_repo_path,
                branch=self.branch)
            ws.apply_patches("minisat", local_repo_path)

    def build(self, ws: Workspace):
        local_repo_path = self.paths.local_repo_path
        build_path = self.paths.build_path

        env = os.environ
        env["CCACHE_BASEDIR"] = str(ws.ws_path.resolve())

        if not build_path.exists():
            os.makedirs(build_path)
            cmake_args = adjusted_cmake_args([
                '-G', 'Ninja', '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
                f'-DCMAKE_CXX_FLAGS=-fuse-ld=gold -fdiagnostics-color=always -fdebug-prefix-map={str(ws.ws_path.resolve())}=. -std=c++11',
            ], self.cmake_adjustments)
            _run(["cmake"] + cmake_args + [local_repo_path], cwd=build_path, env=env)

        _run(["cmake", "--build", "."] + j_from_num_threads(ws.args.num_threads), cwd=build_path, env=env)

        self.include_path = local_repo_path
        self.build_output_path = build_path

    def clean(self, ws: Workspace):
        int_paths = self.paths
        if int_paths.build_path.is_dir():
            shutil.rmtree(int_paths.build_path)
        if ws.args.dist_clean:
            if int_paths.local_repo_path.is_dir():
                shutil.rmtree(int_paths.local_repo_path)
            ws.git_remove_exclude_path(int_paths.local_repo_path)
