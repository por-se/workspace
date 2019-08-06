import os
from pathlib import Path, PurePosixPath
import sys
import subprocess
import re
import shutil

import workspace.util as util
import workspace.build_systems as build_systems
from workspace.settings import settings


def _run(cmd, *args, **kwargs):
    kwargs.setdefault("check", True)
    subprocess.run(cmd, *args, **kwargs)


class Workspace:
    def __init__(self):
        self.ws_path = settings.ws_path

        self.patch_dir = self.ws_path / 'ws-patch'
        self.build_dir = self.ws_path / '.build'
        self._bin_dir = self.ws_path / '.bin'
        self._linker_dirs = {}
        self.builds = []

    @staticmethod
    def get_repository_prefixes():
        return settings.uri_schemes.value

    @staticmethod
    def get_default_linker():
        return settings.default_linker.value

    @staticmethod
    def _check_create_ref_dir():
        if settings.reference_repositories.value is None:
            ref_target_path = Path.home() / '.cache' / 'reference-repos'
            input_res = input(f"Where would you like to store reference repository data? [{ref_target_path}] ")
            if input_res:
                ref_target_path = Path(input_res)

            ref_target_path = ref_target_path.resolve()

            os.makedirs(ref_target_path, exist_ok=True)

            settings.reference_repositories.update(str(ref_target_path))

        if not settings.reference_repositories.value.is_dir():
            if settings.reference_repositories.value.exists():
                raise RuntimeError(
                    f"reference-repository path '{settings.reference_repositories.value}' exists but is not a directory"
                )
            os.makedirs(settings.reference_repositories.value.resolve(), exist_ok=True)

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

    def reference_clone(self, repo_uri, target_path, branch, checkout=True, sparse=None, clone_args=None):  # pylint: disable=too-many-arguments
        if not branch:
            raise ValueError("'branch' is required but not given")

        self._check_create_ref_dir()

        def make_ref_path(git_path):
            name = re.sub("^https://|^ssh://([^/]+@)?|^[^/]+@", "", str(git_path))
            name = re.sub("\\.git$", "", name)
            name = re.sub(":", "/", name)
            return settings.reference_repositories.value / "v1" / name

        def check_ref_dir(ref_dir):
            if not ref_dir.is_dir():
                return False
            try:
                _run(["git", "fsck", "--root", "--no-full"], cwd=ref_dir)
                return True
            except subprocess.CalledProcessError:
                return False

        ref_path = make_ref_path(repo_uri)

        if check_ref_dir(ref_path):
            _run(["git", "-c", f'pack.threads={settings.jobs.value}', "remote", "update", "--prune"], cwd=ref_path)
        else:
            if ref_path.is_dir():
                print(
                    f"Directory is not a valid git repository ('{ref_path}'), deleting and performing a fresh clone..",
                    file=sys.stderr)
                shutil.rmtree(ref_path)
            os.makedirs(ref_path, exist_ok=True)
            _run(["git", "-c", f'pack.threads={settings.jobs.value}', "clone", "--mirror", repo_uri, ref_path])
            _run(["git", "-c", f'pack.threads={settings.jobs.value}', "gc", "--aggressive"], cwd=ref_path)

        clone_command = [
            "git", "-c", f'pack.threads={settings.jobs.value}', "clone", "--reference", ref_path, repo_uri, target_path,
            "--branch", branch
        ]
        if not checkout or sparse is not None:
            clone_command += ["--no-checkout"]
        clone_command += settings.x_git_clone.value
        if clone_args:
            clone_command += clone_args
        _run(clone_command)

        if sparse is not None:
            _run(["git", "-C", target_path, "config", "core.sparsecheckout", "true"])
            with open(target_path / ".git/info/sparse-checkout", "wt") as file:
                for line in sparse:
                    print(line, file=file)
            _run(["git", "-C", target_path, "checkout", branch])

    def git_add_exclude_path(self, path):
        path = PurePosixPath(path)
        path = path.relative_to(self.ws_path)

        git_dir = self.ws_path / ".git"
        assert git_dir.is_dir()

        git_info_dir = git_dir / "info"
        os.makedirs(git_info_dir, exist_ok=True)

        git_exclude_path = git_info_dir / "exclude"

        has_line_end = True  # empty file
        if git_exclude_path.is_file():
            with open(git_exclude_path, "rt") as file:
                lines = file.read()
                has_line_end = (not lines or lines[-1] == "\n")
                for line in lines.splitlines():
                    if line == f'/{path}':
                        return  # path already excluded

        with open(git_info_dir / "exclude", "at") as file:
            if not has_line_end:
                file.write("\n")
            file.write(f'/{path}\n')

    def git_remove_exclude_path(self, path):
        path = PurePosixPath(path)
        path = path.relative_to(self.ws_path)

        git_exclude_path = self.ws_path / ".git" / "info" / "exclude"
        if not git_exclude_path.is_file():
            return  # nothing to un-exclude

        lines = ""
        with open(git_exclude_path, "rt") as file:
            for line in file.read().splitlines():
                if line != f'/{path}':
                    lines += f'{line}\n'
        with open(git_exclude_path, "wt") as file:
            file.write(lines)

    def apply_patches(self, name, target_path):
        for patch in (self.patch_dir / name).glob("*.patch"):
            _run(f"git apply < {patch}", shell=True, cwd=target_path)

    def _initialize_builds(self):
        for build in self.builds:
            build.initialize(self)

    def setup(self):
        self._initialize_builds()

        for build in self.builds:
            build.setup(self)

    def add_to_env(self, env):
        self._initialize_builds()

        for build in self.builds:
            build.add_to_env(env, self)

    def build(self):
        self._initialize_builds()
        self.setup()

        for build in self.builds:
            build.build(self)

    def clean(self):
        self._initialize_builds()

        for build in self.builds:
            build.clean(self)

        if self._bin_dir.exists():
            shutil.rmtree(self._bin_dir)
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)

        mypycache_dir = settings.ws_path / ".mypy_cache"
        if mypycache_dir.exists():
            shutil.rmtree(mypycache_dir)

    def get_env(self):
        env = os.environ.copy()
        env["CCACHE_BASEDIR"] = str(self.ws_path.resolve())
        return env

    def add_linker_to_env(self, linker: build_systems.Linker, env):
        linker_dir = self.get_linker_dir(linker)
        util.env_prepend_path(env, "PATH", linker_dir.resolve())

    def get_linker_dir(self, linker: build_systems.Linker):
        if not linker in self._linker_dirs:
            linker_name = linker.value
            main_linker_dir = self._bin_dir / "linkers"
            linker_dir = main_linker_dir / linker_name
            if not linker_dir.exists():
                linker_dir.mkdir(parents=True)
                if linker == build_systems.Linker.LD:
                    ld_frontend = "ld"
                else:
                    ld_frontend = f"ld.{linker_name}"
                linker_path = shutil.which(ld_frontend)
                assert linker_path is not None, f"Didn't find linker {linker_name}"
                os.symlink(linker_path, linker_dir / "ld")
            self._linker_dirs[linker] = linker_dir
        return self._linker_dirs[linker]
