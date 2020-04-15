import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

from pyfiglet import Figlet

from workspace import Workspace
from workspace.settings import settings


@dataclass
class Args:
    config: str
    build: bool
    jobs: int
    command: List[str]

    def __init__(self):
        self.config = ""
        self.build = False
        self.jobs = settings.jobs.value
        self.command = []


def parse_args(argv: List[str]) -> Args:
    cmd_name = Path(argv[0]).name
    help_requested, failure = False, False
    args = Args()
    argv = sys.argv[1:]
    while argv:
        # pylint: disable=no-else-break,too-many-branches,too-many-statements
        if argv[0] == "-h" or argv[0] == "--help":
            help_requested = True
            break
        elif argv[0] == '-b' or argv[0] == "--build":
            args.build = True
        elif argv[0] == '-j' or argv[0] == '--jobs':
            try:
                args.jobs = int(argv[1])
                argv = argv[2:]
                continue
            except (IndexError, ValueError):
                failure = True
                break
        elif argv[0].startswith('--jobs='):
            try:
                args.jobs = int(argv[0][7:])
            except (IndexError, ValueError):
                failure = True
                break
        elif argv[0].startswith('-j='):
            try:
                args.jobs = int(argv[0][3:])
            except (IndexError, ValueError):
                failure = True
                break
        elif argv[0].startswith('-j'):
            try:
                args.jobs = int(argv[0][2:])
            except (IndexError, ValueError):
                failure = True
                break
        elif argv[0] in settings.config.choices and not args.config:
            args.config = argv[0]
        elif argv[0] == "--":
            argv = argv[1:]
            break
        else:
            break
        argv = argv[1:]

    if help_requested or failure or not argv:
        print(f'Usage: {cmd_name} [-b] [-h] [-j JOBS] [CONFIG] [--] <command> [args...]', file=sys.stderr)
        print(f'''If the first argument is not a valid configuration name, \
the configuration is determined by the environment variable WS_CONFIG and the configuration file.

Example (for 'release' configuration): ./ws run release which klee
Example (for 'debug' configuration): env WS_CONFIG=debug ./ws run which klee
Example (for using a value from the settings file): ./ws run which klee
Example (for running a command named like an existing configuration): ./ws run -- release
Example (builds and then uses 'debug' configuration, 4 parallel jobs, calls command "--"): ./ws run debug -b -j4 -- --

positional arguments:
  CONFIG                The chosen configuration (choices: {", ".join(settings.config.choices)}) (env: WS_CONFIG)

optional arguments:
  -b, --build           Build the configuration before running the command
  -h, --help            Show this help message and exit
  -j JOBS, --jobs JOBS  The number of parallel jobs to start at once (env: WS_JOBS)
''',
              file=sys.stderr)
        sys.exit(1 if failure else 0)
    else:
        settings.jobs.value = args.jobs

        if args.config:
            settings.config.value = args.config
        else:
            args.config = settings.config.value

        args.command = argv

        return args


def main():
    args = parse_args(sys.argv)

    workspace = Workspace(args.config)

    if args.build:
        figlet = Figlet(font="doom", width=80)
        figlet.width = shutil.get_terminal_size(fallback=(9999, 24))[0]
        print(figlet.renderText(f'Building {args.config}'))
        workspace.build()
        print(figlet.renderText(f'Running command'))

    env = workspace.get_env()
    workspace.add_to_env(env)
    env["WS_CONFIG"] = args.config
    env["WS_CONFIGS"] = args.config
    env["WS_HOME"] = str(settings.ws_path)
    env["WS_JOBS"] = str(settings.jobs.value)

    try:
        os.execvpe(args.command[0], args.command, env)
    except FileNotFoundError:
        print(f'The command {args.command[0]} could not be found.', file=sys.stderr)
        sys.exit(2)
