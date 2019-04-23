import argparse
from workspace.bin.util import ws_path_from_here
from workspace.workspace import Workspace

def main():
    parser = argparse.ArgumentParser(
        description=
        "Activates (adds to the set of default configurations) a config"
    )

    parser.add_argument(
        'config',
        metavar='CONFIG',
        type=str,
        help='The configuration to activate.'
    )

    args = parser.parse_args()

    ws_path = ws_path_from_here()
    ws = Workspace(ws_path)
    if args.config not in ws.active_configs():
        if not (ws_path/'ws-config'/f'{args.config}.toml').is_file():
            print(f'The requested config "{args.config}" does not exist (and is also not active).')
            return 1
        else:
            print(f'Config "{args.config}" is not active.')
            return 0
    else:
        ws.deactivate_config(args.config)
        print(f'Deactivated config "{args.config}".')
        return 0
