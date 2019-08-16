from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

from workspace.settings import settings
from workspace.vcs.git import GitRecipeMixin

from .all_recipes import register_recipe
from .llvm import LLVM
from .recipe import Recipe

if TYPE_CHECKING:
    import hashlib
    from workspace import Workspace


class KLEE_UCLIBC(Recipe, GitRecipeMixin):  # pylint: disable=invalid-name
    default_arguments: Dict[str, Any] = {
        "name": "klee-uclibc",
        "llvm": LLVM.default_arguments["name"],
    }

    argument_schema: Dict[str, Any] = {
        "llvm": str,
    }

    def find_llvm(self, workspace: Workspace) -> LLVM:
        return self._find_previous_build(workspace, "llvm", LLVM)

    def __init__(self, **kwargs):
        GitRecipeMixin.__init__(self, "github://klee/klee-uclibc.git")
        Recipe.__init__(self, **kwargs)

        self.paths = None

    def initialize(self, workspace: Workspace):
        Recipe.initialize(self, workspace)

        @dataclass
        class InternalPaths:
            src_dir: Path
            build_dir: Path
            locale_file: Path

        self.paths = InternalPaths(src_dir=settings.ws_path / self.name,
                                   build_dir=workspace.build_dir / f'{self.name}-{self.digest_str}',
                                   locale_file=workspace.build_dir / "uclibc-locale" / "uClibc-locale-030818.tgz")

    def compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        Recipe.compute_digest(self, workspace, digest)

        digest.update(self.find_llvm(workspace).digest)

    def setup(self, workspace: Workspace):
        self.setup_git(self.paths.src_dir, workspace.patch_dir / "klee-uclibc")

        if not self.paths.locale_file.is_file():
            import urllib.request
            import shutil

            attempt, attempts = 0, 5
            while attempt < attempts:
                with urllib.request.urlopen("https://www.uclibc.org/downloads/uClibc-locale-030818.tgz") as response:
                    os.makedirs(self.paths.locale_file.parent, exist_ok=True)
                    with open(self.paths.locale_file, "wb") as locale_file:
                        shutil.copyfileobj(response, locale_file)
                result = subprocess.run(["tar", "-xOf", self.paths.locale_file], stdout=subprocess.DEVNULL)
                if result.returncode != 0:
                    os.remove(self.paths.locale_file)
                    attempt += 1
                    print(f'Failed downloading uclibc locale data in attempt {attempt}/{attempts}')
                else:
                    break
            if attempt >= attempts:
                raise Exception("Failure downloading locale data")

    def build(self, workspace: Workspace):
        subprocess.run(["rsync", "-a", f'{self.paths.src_dir}/', self.paths.build_dir], check=True)
        locale_build_path = self.paths.build_dir / "extra" / "locale" / self.paths.locale_file.name
        if not locale_build_path.is_file():
            os.symlink(self.paths.locale_file.resolve(), locale_build_path.resolve())

        env = workspace.get_env()

        if not (self.paths.build_dir / '.config').exists():
            llvm = self.find_llvm(workspace)

            subprocess.run(
                ["./configure", "--make-llvm-lib", f"--with-llvm-config={llvm.paths.build_dir}/bin/llvm-config"],
                cwd=self.paths.build_dir,
                env=env,
                check=True)

        subprocess.run(["make", "-j", str(settings.jobs.value)], cwd=self.paths.build_dir, env=env, check=True)


register_recipe(KLEE_UCLIBC)
