import argparse
from workspace.bin.util import ws_from_config_name
from workspace.settings import settings

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

    for config in settings.configs.available:
        ws = ws_from_config_name(config)
        ws.clean(dist_clean=args.dist_clean)
