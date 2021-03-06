from __future__ import annotations

import abc
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, List, Optional, Sequence, Union

import schema

from workspace.recipes.irecipe import IRecipe
from workspace.settings import settings

if TYPE_CHECKING:
    from workspace import Workspace


def get_git_dir() -> Path:
    result = subprocess.run(["git", "rev-parse", "--git-dir"], check=True, capture_output=True, cwd=settings.ws_path)
    git_dir = Path(result.stdout.decode().strip())
    if not git_dir.is_absolute():
        git_dir = settings.ws_path / git_dir
    return git_dir


def add_exclude_path(path: Union[Path, PurePosixPath, str]) -> None:
    path = PurePosixPath(path)
    path = path.relative_to(settings.ws_path)

    git_dir = get_git_dir()
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


def remove_exclude_path(path: Union[Path, PurePosixPath, str]) -> None:
    path = PurePosixPath(path)
    path = path.relative_to(settings.ws_path)

    git_dir = get_git_dir()
    git_exclude_path = git_dir / "info" / "exclude"
    if not git_exclude_path.is_file():
        return  # nothing to un-exclude

    lines = ""
    with open(git_exclude_path, "rt") as file:
        for line in file.read().splitlines():
            if line != f'/{path}':
                lines += f'{line}\n'
    with open(git_exclude_path, "wt") as file:
        file.write(lines)


def _check_create_ref_dir() -> None:
    reference_repositories = settings.reference_repositories.value
    if reference_repositories is None:
        default_path = Path.home() / '.cache' / 'reference-repos'
        input_res = input(f'Where would you like to store reference repository data? [{default_path}] ')
        if input_res:
            reference_repositories = Path(input_res)
        else:
            reference_repositories = default_path

        reference_repositories = reference_repositories.resolve()
        settings.reference_repositories.update(reference_repositories)

    if not reference_repositories.is_dir():
        if reference_repositories.exists():
            raise RuntimeError(f'reference-repository path "{reference_repositories}" exists but is not a directory')
        os.makedirs(reference_repositories.resolve(), exist_ok=True)


def reference_clone(  # pylint: disable=too-many-arguments
        repo_uri: str,
        target_path: Path,
        branch: Optional[str],
        checkout: bool = True,
        sparse: Optional[Sequence[str]] = None,
        clone_args: Optional[Sequence[str]] = None) -> None:

    _check_create_ref_dir()

    def make_ref_path(git_path: str) -> Path:
        name = re.sub("^https://|^ssh://([^/]+@)?|^[^/]+@", "", git_path)
        name = re.sub("\\.git$", "", name)
        name = re.sub(":", "/", name)
        return settings.reference_repositories.value / "v1" / name

    def check_ref_dir(ref_dir: Path) -> bool:
        if not ref_dir.is_dir():
            return False
        result = subprocess.run(["git", "fsck", "--root", "--no-full"], cwd=ref_dir, check=False)
        return result.returncode == 0

    ref_path = make_ref_path(repo_uri)

    if check_ref_dir(ref_path):
        subprocess.run(["git", "-c", f'pack.threads={settings.jobs.value}', "remote", "update", "--prune"],
                       cwd=ref_path,
                       check=True)
    else:
        if ref_path.is_dir():
            print(f"Directory is not a valid git repository ('{ref_path}'), deleting and performing a fresh clone..",
                  file=sys.stderr)
            shutil.rmtree(ref_path)
        os.makedirs(ref_path, exist_ok=True)
        subprocess.run(["git", "-c", f'pack.threads={settings.jobs.value}', "clone", "--mirror", repo_uri, ref_path],
                       check=True)
        subprocess.run(["git", "-c", f'pack.threads={settings.jobs.value}', "gc", "--aggressive"],
                       cwd=ref_path,
                       check=True)

    clone_command: List[Union[str, Path]] = [
        "git", "-c", f'pack.threads={settings.jobs.value}', "clone", "--reference", ref_path, repo_uri, target_path
    ]
    if branch:
        clone_command += ["--branch", branch]
    if not checkout or sparse is not None:
        clone_command += ["--no-checkout"]
    clone_command += settings.x_git_clone.value
    if clone_args:
        clone_command += clone_args
    subprocess.run(clone_command, check=True)

    if sparse is not None:
        subprocess.run(["git", "-C", target_path, "config", "core.sparsecheckout", "true"], check=True)
        with open(target_path / ".git" / "info" / "sparse-checkout", "wt") as file:
            for line in sparse:
                print(line, file=file)

        checkout_command: List[Union[str, Path]] = ["git", "-C", target_path, "checkout"]
        if branch:
            checkout_command.append(branch)
        subprocess.run(checkout_command, check=True)


def add_remote(path: Path, remote_name: str, remote_uri: str, fetch: bool = True) -> None:
    subprocess.run(
        ["git", "-c", f'pack.threads={settings.jobs.value}', "-C", path, "remote", "add", remote_name, remote_uri],
        check=True)

    if fetch:
        subprocess.run(["git", "-c", f'pack.threads={settings.jobs.value}', "-C", path, "fetch", remote_name],
                       check=True)


def apply_patches(patch_dir: Path, target_path: Path) -> None:
    for patch in (patch_dir).glob("*.patch"):
        subprocess.run(f"git apply < {patch}", shell=True, cwd=target_path, check=True)


class GitRecipeMixin(IRecipe, abc.ABC):  # pylint: disable=abstract-method
    """
    The `GitRecipeMixin` must be initialized before the `Recipe` base class.

    Parameters
    ----------
    repository: str, optional
        The repository to clone. It is never optional in the schema: If not provided by the mixin user, it must be
        provided by the workspace user in their configuration.
    branch: str, optional
        The branch to check out. If it is passed as `None`, the schema notes it as optional (i.e., `None` is a valid
        value), but if a value other than `None` is passed, the schema will require this value to be a `str`. Note that
        it is pretty much impossible for a workspace user to pass a `None` value directly, as TOML does not support
        the notion of a null type.
    checkout: bool, optional
        When set to `False`, disables actually checking out the repository.
    sparse: sequence of str, optional
        When not `None`, enables a sparse checkout of the elements of the sequence. E.g., when passing
        `["/foo", "/bar"]`, only the subpaths `/foo` and `/bar` are checked out.
    upstream: str, optional
        An URI to register as an additional remote called "upstream". If it is passed as `None`, the schema notes it as
        optional (i.e., `None` is a valid value), but if a value other than `None` is passed, the schema will require
        this value to be a `str`. Note that it is pretty much impossible for a workspace user to pass a `None` value
        directly, as TOML does not support the notion of a null type.
    """
    def __init__(  # pylint: disable=too-many-arguments
            self,
            repository: Optional[str] = None,
            branch: Optional[str] = None,
            checkout: bool = True,
            sparse: Optional[Sequence[str]] = None,
            upstream: Optional[str] = None) -> None:
        self.update_argument_schema({
            "repository": str,
            "branch": schema.Or(str, None) if branch is None else str,
            "upstream": schema.Or(str, None) if upstream is None else str,
        })

        default_arguments = {"branch": branch, "upstream": upstream}
        if repository is not None:
            default_arguments["repository"] = repository
        self.update_default_arguments(default_arguments)

        self.__checkout = checkout
        self.__sparse = sparse

    @property
    def repository(self) -> str:
        result = self.arguments["repository"]
        assert isinstance(result, str)
        result = settings.uri_schemes.resolve(result)
        return result

    @property
    def branch(self) -> Optional[str]:
        result = self.arguments["branch"]
        assert result is None or isinstance(result, str)
        return result

    @property
    def upstream(self) -> Optional[str]:
        result = self.arguments["upstream"]
        assert result is None or isinstance(result, str)
        if result is not None:
            result = settings.uri_schemes.resolve(result)
        return result

    def setup_git(self, source_dir: Path, patch_dir: Optional[Path]):
        if not source_dir.is_dir():
            add_exclude_path(source_dir)
            reference_clone(self.repository,
                            source_dir,
                            branch=self.branch,
                            checkout=self.__checkout,
                            sparse=self.__sparse)
            if self.upstream:
                add_remote(source_dir, "upstream", self.upstream)
            if patch_dir:
                apply_patches(patch_dir, source_dir)

    def setup(self, workspace: Workspace):
        self.setup_git(self.paths["src_dir"], workspace.patch_dir / self.default_name)
