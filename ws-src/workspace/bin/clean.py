import argparse
from workspace.bin import available_configs, resolve_or_default_configs, ws_path_from_here, ws_from_config

def main():
    parser = argparse.ArgumentParser(
        description=
        "Clean the workspace. Removes all build artefacts, to ensure that the next build starts from scratch."
    )

    parser.add_argument(
        "--dist-clean",
        action='store_true',
        default=False,
        help="Clean fully, e.g., also remove all cloned repositories, etc."
    )

    args = parser.parse_args()

    ws_path = ws_path_from_here()

    configs = available_configs(ws_path)

    for config in configs:
        ws = ws_from_config(ws_path, config)
        ws.clean(dist_clean=args.dist_clean)
