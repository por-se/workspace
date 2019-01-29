import os, shutil
from hashlib import blake2s

from workspace.workspace import Workspace, _run
from workspace.util import j_from_num_threads
from . import Recipe

from pathlib import Path


class MINISAT(Recipe):
    default_name = "minisat"

    def __init__(self,
                 branch,
                 name=default_name,
                 repository="git@github.com:stp/minisat.git",
                 cmake_adjustments=[]):
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

            paths = InternalPaths()
            paths.src_dir = ws.ws_path / self.name
            paths.build_dir = ws.build_dir / f'{self.name}-{self.digest}'
            return paths

        self.digest = _compute_digest(self, ws)
        self.paths = _make_internal_paths(self, ws)

    def setup(self, ws: Workspace):
        if not self.paths.src_dir.is_dir():
            ws.git_add_exclude_path(self.paths.src_dir)
            ws.reference_clone(
                self.repository,
                target_path=self.paths.src_dir,
                branch=self.branch)
            ws.apply_patches("minisat", self.paths.src_dir)

    def build(self, ws: Workspace):
        env = os.environ
        env["CCACHE_BASEDIR"] = str(ws.ws_path.resolve())

        if not self.paths.build_dir.exists():
            os.makedirs(self.paths.build_dir)
            cmake_args = Recipe.adjusted_cmake_args([
                '-G', 'Ninja',
                '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
                f'-DCMAKE_CXX_FLAGS=-fdiagnostics-color=always -fdebug-prefix-map={str(ws.ws_path.resolve())}=. -std=c++11',
                f'-DCMAKE_MODULE_LINKER_FLAGS=-fuse-ld=gold -Xlinker --threads -Xlinker --thread-count={(ws.args.num_threads + 1)//2}',
                f'-DCMAKE_SHARED_LINKER_FLAGS=-fuse-ld=gold -Xlinker --threads -Xlinker --thread-count={(ws.args.num_threads + 1)//2}',
                f'-DCMAKE_EXE_LINKER_FLAGS=-fuse-ld=gold -Xlinker --threads -Xlinker --thread-count={(ws.args.num_threads + 1)//2} -Xlinker --gdb-index',
            ], self.cmake_adjustments)
            _run(["cmake"] + cmake_args + [self.paths.src_dir], cwd=self.paths.build_dir, env=env)

        _run(["cmake", "--build", "."] + j_from_num_threads(ws.args.num_threads), cwd=self.paths.build_dir, env=env)

    def clean(self, ws: Workspace):
        if self.paths.build_dir.is_dir():
            shutil.rmtree(self.paths.build_dir)
        if ws.args.dist_clean:
            if self.paths.src_dir.is_dir():
                shutil.rmtree(self.paths.src_dir)
            ws.git_remove_exclude_path(self.paths.src_dir)
