import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from workspace.vcs.git import get_git_dir


def _emergency_cleanup():
    print(
        "WARNING: This workspace seems to be broken (dependencies could not be loaded). "
        "Will try to remove the virtualenv, so it can be recreated..",
        file=sys.stderr)
    venv_path = Path(".venv")
    if venv_path.exists():
        print(".venv found, deleting...", file=sys.stderr)
        shutil.rmtree(venv_path)
        print("Deleted the virtualenv, please close open workspace-shells and run your workspace command again.",
              file=sys.stderr)
    else:
        print("No virtualenv found, giving up. Please re-clone the workspace and start with a fresh copy.",
              file=sys.stderr)
    sys.exit(1)


try:
    from workspace.settings import settings
except ModuleNotFoundError:
    _emergency_cleanup()


def _confirm(query):
    while True:
        choice = input(f"{query} [y/N]: ").lower()
        if choice == "y":
            return True
        if choice == "n" or choice.strip() == "":
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Fully clean the workspace. "
        "REMOVE EVERYTHING that is not part of the workspace itself. That includes any sources checked out inside it.")

    settings.preserve_settings.add_kwargument(parser)
    settings.bind_args(parser)

    clean_cmd = ["git", "clean", "-xdff"]
    if settings.preserve_settings.value:
        clean_cmd += ["-e", "/ws-settings.toml"]

    en_env = os.environ
    en_env["LC_ALL"] = "C"

    git_dir = get_git_dir()
    exclude_path_exists = (git_dir / "info" / "exclude").exists()

    if sys.stdin.isatty():
        subprocess.run(clean_cmd + ["-n"], check=True, env=en_env)
        if exclude_path_exists:
            print("Would remove .git/info/exclude")
        if not _confirm("Do you really want to remove these files and directories?"):
            return

    subprocess.run(clean_cmd, check=True, env=en_env)
    if exclude_path_exists:
        print("Removing .git/info/exclude")
        try:
            os.unlink(git_dir / "info" / "exclude")
        except FileNotFoundError:
            pass

    if sys.stdin.isatty():
        diff = subprocess.run(["git", "diff", "--quiet"], env=en_env, check=False)
        if diff.returncode == 0:
            diff = subprocess.run(["git", "diff", "--quiet", "--staged"], env=en_env, check=False)
        if diff.returncode != 0:
            subprocess.run(["git", "status"], check=True, env=en_env)
            if not _confirm("Also remove all modifications?"):
                return
        else:
            print("No further modification detected.")
            return

    subprocess.run(["git", "reset", "--", "."], check=True, env=en_env)
    subprocess.run(["git", "checkout", "--", "."], check=True, env=en_env)
    subprocess.run(clean_cmd, check=True, env=en_env)
