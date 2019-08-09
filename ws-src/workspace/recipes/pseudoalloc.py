from dataclasses import dataclass
from hashlib import blake2s
from pathlib import Path
import os
import subprocess
from typing import cast, Dict, List

from workspace.settings import settings
from workspace.workspace import Workspace
from . import Recipe


class PSEUDOALLOC(Recipe):  # pylint: disable=invalid-name,too-many-instance-attributes
    default_name = "pseudoalloc"
    profiles = {
        "release": {
            "cargo_flags": ["--release"],
            "rust_flags": [],
        },
        "debug": {
            "cargo_flags": [],
            "rust_flags": [],
        },
        "rel+debinfo": {
            "cargo_flags": ["--release"],
            "rust_flags": ["-g"],
        },
    }

    def __init__(  # pylint: disable=too-many-arguments
            self,
            profile,
            branch=None,
            name=default_name,
            repository="laboratory://concurrent-symbolic-execution/pseudoalloc.git"):

        super().__init__(name)
        self.branch = branch
        self.profile = profile
        self.repository = repository

        self.paths = None

        assert self.profile in self.profiles, f'[{self.__class__.__name__}] the recipe for {self.name} does not contain a profile "{self.profile}"!'

    def initialize(self, workspace: Workspace):
        def _compute_digest(self, workspace: Workspace):
            del workspace  # unused parameter

            digest = blake2s()
            digest.update(self.name.encode())
            digest.update(self.profile.encode())

            # branch and repository need not be part of the digest, as we will build whatever
            # we find at the target path, no matter what it turns out to be at build time

            return digest.hexdigest()[:12]

        def _make_internal_paths(self, workspace: Workspace):
            @dataclass
            class InternalPaths:
                src_dir: Path
                build_dir: Path
                lib_path: Path
                include_dir: Path

            profile_dir = "debug"
            if "--release" in self.profiles[self.profile]["cargo_flags"]:
                profile_dir = "release"

            build_dir = workspace.build_dir / f'{self.name}-{self.profile}-{self.digest}'
            paths = InternalPaths(src_dir=workspace.ws_path / self.name,
                                  build_dir=build_dir,
                                  lib_path=build_dir / profile_dir / "libpseudoalloc.so",
                                  include_dir=build_dir / "include")
            return paths

        self.digest = _compute_digest(self, workspace)
        self.paths = _make_internal_paths(self, workspace)
        self.repository = Recipe.concretize_repo_uri(self.repository, workspace)

    def setup(self, workspace: Workspace):
        if not self.paths.src_dir.is_dir():
            workspace.git_add_exclude_path(self.paths.src_dir)
            workspace.reference_clone(self.repository, target_path=self.paths.src_dir, branch=self.branch)
            workspace.apply_patches("pseudoalloc", self.paths.src_dir)

    def _configure(self, workspace: Workspace):
        pass

    def build(self, workspace: Workspace):
        cargo_flags = cast(Dict[str, List[str]], self.profiles[self.profile])["cargo_flags"]
        rust_flags = cast(Dict[str, List[str]], self.profiles[self.profile])["rust_flags"]

        cargo_env = os.environ.copy()
        cargo_env["CARGO_TARGET_DIR"] = str(self.paths.build_dir)
        cargo_env["RUSTFLAGS"] = " ".join(rust_flags)

        cargo_cmd = ["cargo", "build", "-j", str(settings.jobs.value)]
        cargo_cmd += cargo_flags
        subprocess.run(cargo_cmd, check=True, cwd=self.paths.src_dir, env=cargo_env)

        assert self.paths.lib_path.exists(), "Could not find libpseudoalloc.so in expected directory"
        assert (self.paths.include_dir / "pseudoalloc.h").exists(), "Could not find pseudoalloc.h in expected directory"
