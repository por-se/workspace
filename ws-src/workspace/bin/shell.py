import argparse
import sys

import shellingham

from workspace.bin.shells import Bash, Fish, Zsh
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

    workspace = ws_from_config_name(settings.config.value)
    env = workspace.get_env()
    workspace.add_to_env(env)
    env["WS_CONFIG"] = config
    env["WS_CONFIGS"] = config
    env["WS_HOME"] = settings.ws_path

    shell = settings.shell.value
    if shell == "auto":
        try:
            shell = shellingham.detect_shell()[0]
        except shellingham.ShellDetectionFailure:
            print("Error: Could not auto-detect shell. Please choose the shell explicitly.")
            sys.exit(1)

    if shell == "bash":
        shell_obj = Bash()
    elif shell == "fish":
        shell_obj = Fish()
    elif shell == "zsh":
        shell_obj = Zsh()
    else:
        raise Exception(f'Unknown shell: "{shell}"')

    prompt_prefix = f"({workspace.ws_path.name}: {settings.config.value}) "
    shell_obj.set_prompt_prefix(prompt_prefix)
    shell_obj.add_cd_build(workspace.builds)
    shell_obj.spawn(env)
