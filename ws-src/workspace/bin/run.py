import os, sys
from pathlib import Path
import shutil

import shellingham

from workspace.bin import ws_path_from_here, ws_from_config

def main():
    cmd_name = Path(sys.argv[0]).name
    if len(sys.argv) < 3:
        print(f"Usage: {cmd_name} <config_name> <command> [args...]", file=sys.stderr)
        print(
            f"Example (for 'release.toml' config): {cmd_name} release which klee",
            file=sys.stderr)
        sys.exit(1)

    config_name = sys.argv[1]

    ws_path = ws_path_from_here()

    config_path = ws_path/'ws-config'/f"{config_name}.toml"
    if not config_path.exists():
        print(f"configuration '{config_name}' not found at '{config_path}'")
        sys.exit(1)

    ws = ws_from_config(ws_path, config_path)
    env = ws.get_env()
    ws.add_to_env(env)
    env["VIRTUAL_ENV_DISABLE_PROMPT"] = "1"

    # yes, the `str()` is actually necessary
    env["WS_ENV_CONFIGURATION"] = str(config_name)

    os.execvpe("pipenv", [
        shutil.which("pipenv"),
        "run",
        ] + sys.argv[2:], env)
