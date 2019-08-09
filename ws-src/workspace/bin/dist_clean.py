import argparse
import subprocess
import sys
import os

from workspace.settings import settings


def _confirm(query):
    while True:
        choice = input(f"{query} [y/N]: ").lower()
        if choice == "y":
            return True
        if choice == "n" or choice.strip() == "":
            return False


def main():
    parser = argparse.ArgumentParser(
        description=
        "Fully clean the workspace. REMOVE EVERYTHING that is not part of the workspace itself. That includes any sources checked out inside it."
    )

    settings.preserve_settings.add_kwargument(parser)
    settings.bind_args(parser)

    clean_cmd = ["git", "clean", "-xdff"]
    if settings.preserve_settings.value:
        clean_cmd += ["-e", "/ws-settings.toml"]

    en_env = os.environ
    en_env["LC_ALL"] = "C"

    exclude_path_exists = (settings.ws_path / ".git/info/exclude").exists()

    if sys.stdin.isatty:
        subprocess.run(clean_cmd + ["-n"], check=True, env=en_env)
        if exclude_path_exists:
            print("Would remove .git/info/exclude")
        if not _confirm("Do you really want to remove these files and directories?"):
            return

    subprocess.run(clean_cmd, check=True, env=en_env)
    if exclude_path_exists:
        print("Removing .git/info/exclude")
        try:
            os.unlink(settings.ws_path / ".git/info/exclude")
        except FileNotFoundError:
            pass

    if sys.stdin.isatty:
        subprocess.run(["git", "status"], check=True, env=en_env)
        if not _confirm("Also remove all modifications?"):
            return

    subprocess.run(["git", "reset", "--", "."], check=True, env=en_env)
    subprocess.run(["git", "checkout", "--", "."], check=True, env=en_env)
    subprocess.run(clean_cmd, check=True, env=en_env)
