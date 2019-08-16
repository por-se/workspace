import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import List, Optional, Sequence, Union

from workspace.settings import settings


def add_exclude_path(path: Union[Path, PurePosixPath, str]) -> None:
    path = PurePosixPath(path)
    path = path.relative_to(settings.ws_path)

    git_dir = settings.ws_path / ".git"
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

    git_exclude_path = settings.ws_path / ".git" / "info" / "exclude"
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
        input_res = input(f"Where would you like to store reference repository data? [{default_path}] ")
        if input_res:
            reference_repositories = Path(input_res)
        else:
            reference_repositories = default_path

        reference_repositories = reference_repositories.resolve()
        settings.reference_repositories.update(reference_repositories)

    if not reference_repositories.is_dir():
        if reference_repositories.exists():
            raise RuntimeError(f"reference-repository path '{reference_repositories}' exists but is not a directory")
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
        try:
            subprocess.run(["git", "fsck", "--root", "--no-full"], cwd=ref_dir, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

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
        with open(target_path / ".git/info/sparse-checkout", "wt") as file:
            for line in sparse:
                print(line, file=file)

        checkout_command: List[Union[str, Path]] = ["git", "-C", target_path, "checkout"]
        if branch:
            checkout_command.append(branch)
        subprocess.run(checkout_command, check=True)


def apply_patches(patch_dir: Path, name: Union[str, Path], target_path: Path) -> None:
    for patch in (patch_dir / name).glob("*.patch"):
        subprocess.run(f"git apply < {patch}", shell=True, cwd=target_path, check=True)
