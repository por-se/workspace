import os, sys, subprocess, re, multiprocessing
from pathlib import Path

import workspace_base.util as util


def _run(cmd, *args, **kwargs):
    kwargs.setdefault("check", True)
    subprocess.run(cmd, *args, **kwargs)


class Workspace:
    def __init__(self, ws_path):
        if not ws_path:
            raise RuntimeException("'ws_path' not set")

        # make sure we have a Path, Path(Path()) is just Path()
        ws_path = Path(ws_path)

        self.ws_path = ws_path
        self.ref_dir = self.ws_path / '.ref'
        self.patch_dir = self.ws_path / 'patch'
        self.build_dir = self.ws_path / '.build'
        self.builds = []

    def __check_create_ref_dir(self):
        if not self.ref_dir.is_dir():
            if self.ref_dir.exists():
                raise RuntimeError(
                    f"reference-repository path '{self.ref_dir}' exists but is not a directory"
                )

            if self.ref_dir.is_symlink():
                os.makedirs(self.ref_dir.resolve(), exist_ok=True)
            else:
                ref_target_path = Path.home(
                ) / '.cache/reference-repos'
                input_res = input(f"Where would you like to story reference repository data? [{ref_target_path}] ")
                if input:
                    ref_target_path = Path(input_res)

                ref_target_path = ref_target_path.resolve()

                os.makedirs(ref_target_path, exist_ok=True)

                if ref_target_path != self.ref_dir:
                    self.ref_dir.symlink_to(ref_target_path)

    def set_builds(self, builds):
        self.builds = builds

    def find_build(self, build_name, before=None):
        i = 0

        while i < len(self.builds):
            if before and self.builds[i] == before:
                return None

            if self.builds[i].name == build_name:
                return self.builds[i]

            i += 1

        return None

    def reference_clone(self, repo_uri, target_path, branch, clone_args=[]):
        def make_ref_path(git_path):
            name = re.sub("^https://|^ssh://|^[^/]+@", "", str(git_path))
            name = re.sub("\.git$", "", name)
            name = re.sub(":", "/", name)
            return self.ref_dir / "v1" / name

        ref_path = make_ref_path(repo_uri)

        self.__check_create_ref_dir()

        if ref_path.is_dir():
            _run(["git", "remote", "update", "--prune"], cwd=ref_path)
        else:
            os.makedirs(ref_path, exist_ok=True)
            _run(["git", "clone", "--mirror", repo_uri, ref_path])
            _run(["git", "gc", "--aggressive"], cwd=ref_path)

        _run([
            "git", "clone", "--reference", ref_path, repo_uri, target_path,
            "--branch", branch
        ] + clone_args)

    def apply_patches(self, name, target_path):
        for patch in (self.patch_dir / name).glob("*.patch"):
            _run(f"git apply < {patch}", shell=True, cwd=target_path)

    def add_to_env(self, env):
        for build in self.builds:
            build.add_to_env(env, self)

    def main(self):
        parser = util.EnvVarArgumentParser(description="build this workspace")
        parser.add_argument(
            '-j',
            '--num_threads',
            type=int,
            default=multiprocessing.cpu_count(),
            help="specify number of threads to use in parallel")
        self.args = parser.parse_args()

        self.__check_create_ref_dir()

        for build in self.builds:
            build.build(self)
