from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING, Dict, List, cast

from workspace.settings import settings
from workspace.vcs.git import GitRecipeMixin

from .all_recipes import register_recipe
from .recipe import Recipe

if TYPE_CHECKING:
    from workspace import Workspace


class PSEUDOALLOC(Recipe, GitRecipeMixin):  # pylint: disable=invalid-name
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

    def __init__(self, **kwargs):
        GitRecipeMixin.__init__(self, "laboratory://symbiosys/projects/concurrent-symbolic-execution/pseudoalloc.git")
        Recipe.__init__(self, **kwargs)

    def initialize(self, workspace: Workspace):
        Recipe.initialize(self, workspace)

        profile_dir_name = "debug"
        if "--release" in self.profile["cargo_flags"]:
            profile_dir_name = "release"

        self.paths["include_dir"] = self.paths["build_dir"] / "include"
        self.paths["libpseudoalloc"] = self.paths["build_dir"] / profile_dir_name / "libpseudoalloc.so"

    def build(self, workspace: Workspace):
        cargo_flags = cast(Dict[str, List[str]], self.profile["cargo_flags"])
        rust_flags = cast(Dict[str, List[str]], self.profile["rust_flags"])

        cargo_env = os.environ.copy()
        cargo_env["CARGO_TARGET_DIR"] = str(self.paths["build_dir"])
        cargo_env["RUSTFLAGS"] = " ".join(rust_flags)

        cargo_cmd = ["cargo", "build", "-j", str(settings.jobs.value)]
        cargo_cmd += cargo_flags
        subprocess.run(cargo_cmd, check=True, cwd=self.paths["src_dir"], env=cargo_env)

        assert self.paths["libpseudoalloc"].exists(), "Could not find libpseudoalloc.so at expected location"
        assert (self.paths["include_dir"] /
                "pseudoalloc.h").exists(), "Could not find pseudoalloc.h in expected directory"


register_recipe(PSEUDOALLOC)
