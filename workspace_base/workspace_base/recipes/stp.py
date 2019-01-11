import os, multiprocessing, shutil

from workspace_base.workspace import Workspace, _run
from workspace_base.util import j_from_num_threads
from . import Recipe, MINISAT

from pathlib import Path


class STP(Recipe):
    default_name = "stp"

    def __init__(self,
                 branch,
                 name=default_name,
                 repository="git@github.com:stp/stp.git",
                 minisat_name=MINISAT.default_name):
        super().__init__(name)
        self.branch = branch
        self.repository = repository
        self.minisat_name = minisat_name

    def _make_internal_paths(self, ws: Workspace):
        class InternalPaths:
            pass

        res = InternalPaths()
        res.local_repo_path = ws.ws_path / self.name
        res.build_path = ws.build_dir / self.name
        return res

    def build(self, ws: Workspace):
        int_paths = self._make_internal_paths(ws)

        local_repo_path = int_paths.local_repo_path
        if not local_repo_path.is_dir():
            ws.reference_clone(
                self.repository,
                target_path=local_repo_path,
                branch=self.branch)
            ws.apply_patches("stp", local_repo_path)

        build_path = int_paths.build_path
        if not build_path.exists():
            os.makedirs(build_path)

            minisat = ws.find_build(build_name=self.minisat_name, before=self)

            assert minisat, "STP requires minisat"

            cmake_args = [
                '-G', 'Ninja', '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
                f'-DMINISAT_LIBRARY={minisat.build_output_path}/libminisat.a',
                f'-DMINISAT_INCLUDE_DIR={minisat.include_path}',
                '-DNOCRYPTOMINISAT=On', '-DBUILD_SHARED_LIBS=Off',
                '-DENABLE_PYTHON_INTERFACE=Off', '-DENABLE_ASSERTIONS=On',
                '-DSANITIZE=Off', '-DSTATICCOMPILE=On',
                '-DCMAKE_CXX_FLAGS=-std=c++11 -fuse-ld=gold -fdiagnostics-color=always',
                local_repo_path
            ]

            _run(["cmake"] + cmake_args, cwd=build_path)

        _run(["cmake", "--build", "."] + j_from_num_threads(ws.args.num_threads), cwd=build_path)

        self.build_output_path = build_path
        self.stp_dir = local_repo_path

    def clean(self, ws: Workspace):
        int_paths = self._make_internal_paths(ws)
        if int_paths.build_path.is_dir():
            shutil.rmtree(int_paths.build_path)
        if ws.args.dist_clean and int_paths.local_repo_path.is_dir():
            shutil.rmtree(int_paths.local_repo_path)
