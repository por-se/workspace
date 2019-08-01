import os, sys
from pathlib import Path
import shutil

import argparse
import shellingham

from workspace.bin.util import ws_from_config_name
from workspace.settings import settings


def main():
    parser = argparse.ArgumentParser(
        description="Activates a shell with an environment suitable for the given configuration.")

    settings.config.add_argument(parser)
    settings.shell.add_kwargument(parser)
    settings.bind_args(parser)

    config = settings.config.value
    if config is None:
        print(f'Error: Setting "{settings.config.name}" is not set', file=sys.stderr)
        print(file=sys.stderr)
        parser.print_help(sys.stderr)
        sys.exit(1)

    ws = ws_from_config_name(settings.config.value)
    env = ws.get_env()
    ws.add_to_env(env)
    env["VIRTUAL_ENV_DISABLE_PROMPT"] = "1"
    env["WS_CONFIG"] = config
    env["WS_CONFIGS"] = config

    shell = settings.shell.value
    if shell == "auto":
        try:
            shell = shellingham.detect_shell()[0]
        except shellingham.ShellDetectionFailure:
            print("Error: Could not auto-detect shell. Please choose the shell explicitly.")
            sys.exit(1)

    if shell == "bash":
        prompt_cmd = f"PS1=\"({settings.ws_path.name}) ({config}) $PS1\""
    elif shell == "zsh":
        prompt_cmd = f"PROMPT=\"({settings.ws_path.name}) ({config}) $PROMPT\""
    elif shell == "fish":
        prompt_cmd = f"functions -c fish_prompt _fish_nested_prompt ; function fish_prompt ; printf \"\\n%s\" \"({settings.ws_path.name}) ({config}) \" ; _fish_nested_prompt ; end"
    else:
        raise Exception(f'Unknown shell: "{shell}"')

    # need "--anyway" as we are already running in a pipenv context, so pipenv believes it should not spawn a shell..
    os.execvpe("pipenv", [
        "pipenv",
        "shell",
        "--anyway",
        prompt_cmd,
    ], env)
