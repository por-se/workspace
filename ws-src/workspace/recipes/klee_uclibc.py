from __future__ import annotations

import os
import shutil
import subprocess
import urllib.request
from typing import TYPE_CHECKING, Any, Dict

from workspace.settings import settings
from workspace.util import env_prepend_path, run_with_prefix
from workspace.vcs.git import GitRecipeMixin

from .all_recipes import register_recipe
from .llvm import LLVM
from .recipe import Recipe

if TYPE_CHECKING:
    import hashlib
    from .porse import PORSE
    from workspace import Workspace


class KLEE_UCLIBC(Recipe, GitRecipeMixin):  # pylint: disable=invalid-name
    default_arguments: Dict[str, Any] = {
        "llvm": LLVM().default_name,
        "porse": "porse",  # hard-coded to avoid a circular dependency
    }

    argument_schema: Dict[str, Any] = {
        "llvm": str,
        "porse": str,
    }

    def find_llvm(self, workspace: Workspace) -> LLVM:
        return self._find_previous_build(workspace, "llvm", LLVM)

    def find_porse(self, workspace: Workspace) -> PORSE:
        return workspace.find_build(self.porse, before=None)

    @property
    def porse(self):
        return self.arguments["porse"]

    def __init__(self, **kwargs):
        GitRecipeMixin.__init__(self, "github://por-se/klee-uclibc.git")
        Recipe.__init__(self, **kwargs)

    def initialize(self, workspace: Workspace):
        Recipe.initialize(self, workspace)

        self.paths["locale_file"] = workspace.build_dir / "uclibc-locale" / "uClibc-locale-030818.tgz"

        porse = self.find_porse(workspace)
        if self.name != porse.klee_uclibc:
            raise Exception(f'[{self.name}] The {porse.__class__.__name__} build named "{porse.name}" '
                            f'must use the {self.__class__.__name__} build named "{self.name}"')

    def compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        Recipe.compute_digest(self, workspace, digest)

        porse = self.find_porse(workspace)
        # porse include dir is known at this time as it does not depend on the digest
        # and is independent of build arguments for the porse recipe
        digest.update(f'porse-include-dir:{porse.paths["include_dir"].relative_to(settings.ws_path)}'.encode())

        digest.update(self.find_llvm(workspace).digest)

    def setup(self, workspace: Workspace):
        self.setup_git(self.paths["src_dir"], workspace.patch_dir / self.default_name)

        if not self.paths["locale_file"].is_file():
            attempt, attempts = 0, 5
            while attempt < attempts:
                with urllib.request.urlopen("https://www.uclibc.org/downloads/uClibc-locale-030818.tgz") as response:
                    os.makedirs(self.paths["locale_file"].parent, exist_ok=True)
                    with open(self.paths["locale_file"], "wb") as locale_file:
                        shutil.copyfileobj(response, locale_file)
                result = subprocess.run(["tar", "-xOf", self.paths["locale_file"]],
                                        stdout=subprocess.DEVNULL,
                                        check=False)
                if result.returncode != 0:
                    os.remove(self.paths["locale_file"])
                    attempt += 1
                    print(f'Failed downloading uclibc locale data in attempt {attempt}/{attempts}')
                else:
                    break
            if attempt >= attempts:
                raise Exception("Failure downloading locale data")

    def build(self, workspace: Workspace):
        run_with_prefix(["rsync", "-a", f'{self.paths["src_dir"]}/', self.paths["build_dir"]],
                        self.output_prefix,
                        check=True)
        locale_build_path = self.paths["build_dir"] / "extra" / "locale" / self.paths["locale_file"].name
        if not locale_build_path.is_file():
            os.symlink(self.paths["locale_file"].resolve(), locale_build_path.resolve())

        env = workspace.get_env()
        porse = self.find_porse(workspace)

        env_prepend_path(env, "C_INCLUDE_PATH", porse.paths["include_dir"])

        if not (self.paths["build_dir"] / '.config').exists():
            llvm = self.find_llvm(workspace)

            run_with_prefix(["./configure", "--make-llvm-lib", f'--with-llvm-config={llvm.paths["llvm-config"]}'],
                            self.output_prefix,
                            cwd=self.paths["build_dir"],
                            env=env,
                            check=True)

        run_with_prefix(["make", "-j", str(settings.jobs.value)],
                        self.output_prefix,
                        cwd=self.paths["build_dir"],
                        env=env,
                        check=True)


register_recipe(KLEE_UCLIBC)
