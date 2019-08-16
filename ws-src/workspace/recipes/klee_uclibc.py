from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from hashlib import blake2s
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

import schema

from workspace.settings import settings
from workspace.vcs import git

from .all_recipes import register_recipe
from .llvm import LLVM
from .recipe import Recipe

if TYPE_CHECKING:
    from workspace import Workspace


class KLEE_UCLIBC(Recipe):  # pylint: disable=invalid-name
    default_arguments: Dict[str, Any] = {
        "name": "klee-uclibc",
        "repository": "github://klee/klee-uclibc.git",
        "branch": None,
        "llvm": LLVM.default_arguments["name"],
        "cmake-adjustments": [],
    }

    argument_schema: Dict[str, Any] = {
        "name": str,
        "repository": str,
        "branch": schema.Or(str, None),
        "llvm": str,
        "cmake-adjustments": [str],
    }

    @property
    def branch(self) -> str:
        return self.arguments["branch"]

    @property
    def cmake_adjustments(self) -> List[str]:
        return self.arguments["cmake-adjustments"]

    def find_llvm(self, workspace: Workspace) -> LLVM:
        return self._find_previous_build(workspace, "llvm", LLVM)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cmake = None
        self.paths = None
        self.repository = None

    def initialize(self, workspace: Workspace):
        def _compute_digest(self, workspace: Workspace):
            digest = blake2s()
            digest.update(self.name.encode())

            # branch and repository need not be part of the digest, as we will build whatever
            # we find at the target path, no matter what it turns out to be at build time

            digest.update(self.find_llvm(workspace).digest.encode())

            return digest.hexdigest()[:12]

        def _make_internal_paths(self, workspace: Workspace):
            @dataclass
            class InternalPaths:
                src_dir: Path
                build_dir: Path
                locale_file: Path

            paths = InternalPaths(src_dir=settings.ws_path / self.name,
                                  build_dir=workspace.build_dir / f'{self.name}-{self.digest}',
                                  locale_file=workspace.build_dir / "uclibc-locale" / "uClibc-locale-030818.tgz")
            return paths

        self.digest = _compute_digest(self, workspace)
        self.paths = _make_internal_paths(self, workspace)
        self.repository = settings.uri_schemes.resolve(self.arguments["repository"])

    def setup(self, workspace: Workspace):
        if not self.paths.src_dir.is_dir():
            git.add_exclude_path(self.paths.src_dir)
            git.reference_clone(self.repository, target_path=self.paths.src_dir, branch=self.branch)
            git.apply_patches(workspace.patch_dir, "klee-uclibc", self.paths.src_dir)

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
