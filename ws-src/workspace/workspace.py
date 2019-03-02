import os, sys, subprocess, re
from pathlib import Path, PurePosixPath
import shutil

import schema, toml

import workspace.util as util


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
        self._load_config()

        self.ref_dir = Path(self._config['reference']) if 'reference' in self._config else None
        self.patch_dir = self.ws_path / 'ws-patch'
        self.build_dir = self.ws_path / '.build'
        self._bin_dir = self.ws_path / '.bin'
        self.builds = []

    def _load_config(self):
        try:
            with open(self.ws_path/'.ws-config.toml') as f:
                config = toml.load(f)

            self._config = schema.Schema({
                schema.Optional('reference'): schema.And(str, len),
                'active configs': schema.And(schema.Use(set), {
                    schema.And(str, len),
                }),
                'repository_prefixes': schema.Schema({str: str})
            }).validate(config)
        except FileNotFoundError:
            self._config = {
                'active configs': {
                    'release'
                },
                'repository_prefixes': {
                    'github://': "ssh://git@github.com/",
                    'laboratory://': "ssh://git@laboratory.comsys.rwth-aachen.de/",
                },
            }
            self._store_config()

    def _store_config(self):
        with open(self.ws_path/'.ws-config.toml', 'wt') as f:
            toml.dump(self._config, f)

    def activate_config(self, config: str):
        self._config['active configs'].add(config)
        self._store_config()

    def deactivate_config(self, config: str):
        self._config['active configs'].remove(config)
        self._store_config()

    def active_configs(self):
        return self._config['active configs']

    def get_repository_prefixes(self):
        return self._config['repository_prefixes']

    def _check_create_ref_dir(self):
        if self.ref_dir is None:
            ref_target_path = Path.home()/'.cache'/'reference-repos'
            input_res = input(f"Where would you like to store reference repository data? [{ref_target_path}] ")
            if input_res:
                ref_target_path = Path(input_res)

            ref_target_path = ref_target_path.resolve()

            os.makedirs(ref_target_path, exist_ok=True)

            self.ref_dir = ref_target_path
            self._config["reference"] = str(ref_target_path)
            self._store_config()

        if not self.ref_dir.is_dir():
            if self.ref_dir.exists():
                raise RuntimeError(
                    f"reference-repository path '{self.ref_dir}' exists but is not a directory"
                )
            else:
                os.makedirs(self.ref_dir.resolve(), exist_ok=True)

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

    def reference_clone(self, repo_uri, target_path, branch, checkout=True, sparse=None, clone_args=[]):
        self._check_create_ref_dir()

        def make_ref_path(git_path):
            name = re.sub("^https://|^ssh://([^/]+@)?|^[^/]+@", "", str(git_path))
            name = re.sub("\.git$", "", name)
            name = re.sub(":", "/", name)
            return self.ref_dir / "v1" / name

        ref_path = make_ref_path(repo_uri)

        if ref_path.is_dir():
            _run(["git", "remote", "update", "--prune"], cwd=ref_path)
        else:
            os.makedirs(ref_path, exist_ok=True)
            _run(["git", "clone", "--mirror", repo_uri, ref_path])
            _run(["git", "gc", "--aggressive"], cwd=ref_path)

        clone_command = [
            "git", "clone", "--reference", ref_path, repo_uri, target_path,
            "--branch", branch
        ]
        if checkout == False or sparse is not None:
            clone_command += ["--no-checkout"]
        _run(clone_command + clone_args)

        if sparse is not None:
            _run(["git", "-C", target_path, "config", "core.sparsecheckout", "true"])
            with open(target_path / ".git/info/sparse-checkout", "wt") as f:
                for line in sparse:
                    print(line, file=f)
            _run(["git", "-C", target_path, "checkout", branch])

    def git_add_exclude_path(self, path):
        path = PurePosixPath(path)
        path = path.relative_to(self.ws_path)

        git_dir = self.ws_path / ".git"
        assert git_dir.is_dir()

        git_info_dir = git_dir / "info"
        os.makedirs(git_info_dir, exist_ok=True)

        git_exclude_path = git_info_dir / "exclude"

        has_line_end = True # empty file
        if git_exclude_path.is_file():
            with open(git_exclude_path, "rt") as f:
                lines = f.read()
                has_line_end = (len(lines) == 0 or lines[-1] == "\n")
                for line in lines.splitlines():
                    if line == f'/{path}':
                        return # path already excluded

        with open(git_info_dir / "exclude", "at") as f:
            if not has_line_end:
                f.write("\n")
            f.write(f'/{path}\n')

    def git_remove_exclude_path(self, path):
        path = PurePosixPath(path)
        path = path.relative_to(self.ws_path)

        git_exclude_path = self.ws_path / ".git" / "info" / "exclude"
        if not git_exclude_path.is_file():
            return # nothing to un-exclude

        lines = ""
        with open(git_exclude_path, "rt") as f:
            for line in f.read().splitlines():
                if line != f'/{path}':
                    lines += f'{line}\n'
        with open(git_exclude_path, "wt") as f:
            f.write(lines)

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

    def build(self, num_threads):
        self._initialize_builds()
        self.setup()

        self.args = util.EmptyClass()
        self.args.num_threads = num_threads

        self._check_create_ref_dir()

        for build in self.builds:
            build.build(self)

    def clean(self, dist_clean):
        self._initialize_builds()

        self.args = util.EmptyClass()
        self.args.dist_clean = dist_clean

        for build in self.builds:
            build.clean(self)

        if self._bin_dir.exists():
            shutil.rmtree(self._bin_dir)
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)

        if dist_clean:
            config_file = self.ws_path/".ws-config.toml"
            if config_file.exists():
                os.remove(config_file)

            pipfile = self.ws_path/"Pipfile.lock"
            if pipfile.exists():
                os.remove(pipfile)
            egg_dir = self.ws_path/"ws-src"/"workspace.egg-info"
            if egg_dir.exists():
                shutil.rmtree(egg_dir)
            venv_dir = self.ws_path/".venv"
            if venv_dir.exists():
                shutil.rmtree(venv_dir)

    def get_env(self):
        if not self._bin_dir.is_dir():
            ld = shutil.which('ld.lld')
            assert ld is not None, "Felix says: Install lld!"

            os.makedirs(self._bin_dir)
            os.symlink(ld, self._bin_dir/'ld')

        env = os.environ.copy()
        env["CCACHE_BASEDIR"] = str(self.ws_path.resolve())
        util.env_prepend_path(env, "PATH", self._bin_dir.resolve())
        return env
