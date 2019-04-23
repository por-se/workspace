import os, sys
from pathlib import Path
import shutil

import shellingham

from workspace.bin.util import ws_path_from_here, ws_from_config


def main():
    cmd_name = Path(sys.argv[0]).name
    if len(sys.argv) != 2:
        print(f"Usage: {cmd_name} <config_name>", file=sys.stderr)
        print(
            f"Example (for 'release.toml' config): {cmd_name} release",
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

    shell = shellingham.detect_shell()[0]
    if shell == "bash":
        prompt_cmd = f"PS1=\"({ws_path.name}) ({config_name}) $PS1\""
    elif shell == "zsh":
        prompt_cmd = f"PROMPT=\"({ws_path.name}) ({config_name}) $PROMPT\""
    elif shell == "fish":
        prompt_cmd = f"functions -c fish_prompt _fish_nested_prompt ; function fish_prompt ; printf \"\\n%s\" \"({ws_path.name}) ({config_name}) \" ; _fish_nested_prompt ; end"

    # need "--anyway" as we are already running in a pipenv context, so pipenv believes it should not spawn a shell..
    os.execvpe("pipenv", [
        shutil.which("pipenv"),
        "shell",
        "--anyway",
        prompt_cmd,
    ], env)
