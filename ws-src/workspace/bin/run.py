import os, sys
from pathlib import Path
import shutil

from workspace.settings import settings
from workspace.bin.util import ws_from_config_name

def main():
    cmd_name = Path(sys.argv[0]).name
    if len(sys.argv) < 2 or sys.argv[1] == "-h" or sys.argv[1] == "--help":
        print(f'Usage: {cmd_name} [configuration_name] [--] <command> [args...]', file=sys.stderr)
        print(
f'''If the first argument is not a valid configuration name, the configuration is determined by the environment variable WS_CONFIG and the configuration file.

Example (for 'release' configuration): ./ws run release which klee
Example (for 'debug' configuration): env WS_CONFIG=debug ./ws run which klee
Example (for using a value from the settings file): ./ws run which klee''',
            file=sys.stderr)
        sys.exit(0)

    config_name = str(sys.argv[1])
    if config_name not in settings.config.available:
        config_name = settings.config.value
        if config_name is None:
            print(f'"{sys.argv[1]}" is not a valid configuration and the setting "config" is not set', file=sys.stderr)
            sys.exit(1)
        command = sys.argv[1:]
    else:
        command = sys.argv[2:]

    if len(command) > 0 and command[0] == "--":
        command = command[1:]

    if len(command) == 0:
        print('No command specified')
        sys.exit(1)

    ws = ws_from_config_name(config_name)
    env = ws.get_env()
    ws.add_to_env(env)
    env["VIRTUAL_ENV_DISABLE_PROMPT"] = "1"
    env["WS_CONFIG"] = config_name
    env["WS_CONFIGS"] = config_name

    os.execvpe("pipenv", [
        shutil.which("pipenv"),
        "run",
        ] + command, env)
