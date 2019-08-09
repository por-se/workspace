import argparse

from workspace.bin.util import ws_from_config_name
from workspace.settings import settings


def main():
    parser = argparse.ArgumentParser(
        description=
        "Clean the workspace. Removes all build artifacts, to ensure that the next build starts from scratch.")

    settings.bind_args(parser)

    for config in settings.configs.available:
        workspace = ws_from_config_name(config)
        workspace.clean()
