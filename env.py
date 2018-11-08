#!/usr/bin/env python3
import os, shutil, subprocess, sys

from pathlib import Path
from pprint import pprint


def main():
    if len(sys.argv) != 2:
        print("Usage: ./env.py <configuration name>", file=sys.stderr)
        print(
            "Example (for 'default.toml' config): ./env.py default",
            file=sys.stderr)
        sys.exit(1)

    config_name = sys.argv[1]

    env = os.environ.copy()
    env["VIRTUAL_ENV_DISABLE_PROMPT"] = "1"

    ws_path = Path(__file__).parent.resolve()

    config_path = ws_path / 'build_configs' / 'available' / f"{config_name}.toml"
    if not config_path.exists():
        print(f"configuration '{config_name}' not found at '{config_path}'")
        sys.exit(1)

    # yes, the `str()` is actually necessary
    env["WS_ENV_CONFIGURATION"] = str(config_name)

    os.execvpe("pipenv", [
        shutil.which("pipenv"), "shell",
        f"PROMPT=\"({ws_path.name}) ({config_name}) $PROMPT\""
    ], env)


if __name__ == "__main__":
    main()
