import argparse
from workspace.bin.util import available_configs, resolve_or_default_configs, ws_path_from_here, ws_from_config

def main():
    parser = argparse.ArgumentParser(
        description=
        "Setup (usually download sources) one or more configurations. By default, setups all configurations, or only the configuration of the current environment if one is active."
    )

    choice_group = parser.add_mutually_exclusive_group()
    choice_group.add_argument(
        'configs',
        metavar='CONFIG',
        type=str,
        nargs='*',
        default=False,
        help="The configurations to build")
    choice_group.add_argument(
        '-a',
        '--all',
        action='store_true',
        help="build all available configs")

    args = parser.parse_args()

    ws_path = ws_path_from_here()

    configs = available_configs(ws_path) if args.all else resolve_or_default_configs(ws_path, args.configs)

    for config in configs:
        ws = ws_from_config(ws_path, config)
        ws.setup()
