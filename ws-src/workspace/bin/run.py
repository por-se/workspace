import argparse
import os
import shutil
import sys

from pyfiglet import Figlet

from workspace import Workspace
from workspace.settings import settings


def main():
    parser = argparse.ArgumentParser(
        description='Runs a command inside the workspace set up with a chosen configuration. In case the command'
        ' conflicts with an argument or configuration, use two dashes to separate the command to be run (e.g.,'
        ' `run -- --my-weird-command`)')

    settings.config.add_argument(parser)
    settings.jobs.add_kwargument(parser)
    parser.add_argument('-b',
                        '--build',
                        action="store_true",
                        help=f'Build the configuration before running the command')

    argc = 1
    command = []
    while argc < len(sys.argv):
        if sys.argv[argc] == "--":
            command = sys.argv[argc + 1:]
            break
        if sys.argv[argc][0] != "-" and sys.argv[argc] not in settings.config.choices:
            command = sys.argv[argc:]
            break
        argc += 1
    args = parser.parse_args(sys.argv[1:argc])

    if args.config is not None:
        settings.config.value = args.config
    else:
        args.config = settings.config.value
    if args.jobs is not None:
        settings.jobs.value = args.jobs
    else:
        args.jobs = settings.jobs.value

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
        os.execvpe(command[0], command, env)
    except FileNotFoundError:
        print(f'The command {command[0]} could not be found.', file=sys.stderr)
        sys.exit(2)
