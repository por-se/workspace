import argparse
import sys

from workspace.bin.util import ws_from_config_name
from workspace.settings import settings


def main():
    parser = argparse.ArgumentParser(
        description="Print the path of the build directory of the given build for as used inside a configuration")

    settings.build_name.add_argument(parser)
    settings.config.add_kwargument(parser)
    settings.bind_args(parser)

    if not settings.build_name.value:
        print("Cannot determine required setting: Build name is not set", file=sys.stderr)
        sys.exit(1)

    if not settings.config.value:
        print("Cannot determine required setting: Configuration is not set", file=sys.stderr)
        sys.exit(1)

    workspace = ws_from_config_name(settings.config.value)
    workspace.initialize_builds()
    build = [build.paths.build_dir for build in workspace.builds if build.name == settings.build_name.value]
    assert len(build) <= 1
    if not build:
        print(
            f'The configuration "{settings.config.value}" does not contain a build with the name "{settings.build_name.value}".',
            file=sys.stderr)
        sys.exit(1)

    print(build[0])
