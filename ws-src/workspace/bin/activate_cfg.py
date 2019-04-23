import argparse
from workspace.bin.util import ws_path_from_here
from workspace.workspace import Workspace

def main():
    parser = argparse.ArgumentParser(
        description=
        "Activates (adds to the set of default configurations) a config."
    )

    parser.add_argument(
        'config',
        metavar='CONFIG',
        type=str,
        help='The configuration to activate'
    )

    args = parser.parse_args()

    ws_path = ws_path_from_here()
    if not (ws_path/'ws-config'/f'{args.config}.toml').is_file():
        print(f'The requested config "{args.config}" does not exist.')
        return 1

    ws = Workspace(ws_path)
    if args.config in ws.active_configs():
        print(f'Config "{args.config}" is already active.')
        return 0
    else:
        ws.activate_config(args.config)
        print(f'Activated config "{args.config}".')
        return 0
