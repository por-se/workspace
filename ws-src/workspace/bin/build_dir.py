import argparse
import sys

from workspace import Workspace
from workspace.settings import settings


def main():
    if len(sys.argv) <= 1 or sys.argv[1] != "--cd-build-dir":
        cd_build_dir = False
        description = "Print the path of the build directory of a given build as used inside a configuration"
    else:
        cd_build_dir = True
        description = "Change to the build directory of a given build as used inside a configuration"

        # directly setting argv[0] is not possible due to python
        sys.argv[0] = "cd-build-dir"
        del sys.argv[1]

    parser = argparse.ArgumentParser(description=description)

    settings.build_name.add_argument(parser)
    settings.config.add_kwargument(parser)
    settings.bind_args(parser)

    if not settings.build_name.value:
        print("Cannot determine required setting: Build name is not set", file=sys.stderr)
        sys.exit(1)

    if not settings.config.value:
        print("Cannot determine required setting: Configuration is not set", file=sys.stderr)
        sys.exit(1)

    workspace = Workspace(settings.config.value)
    workspace.initialize_builds()
    build = [build.paths["build_dir"] for build in workspace.builds if build.name == settings.build_name.value]
    assert len(build) <= 1
    if not build:
        print(
            f'The configuration "{settings.config.value}" '
            f'does not contain a build with the name "{settings.build_name.value}".',
            file=sys.stderr)
        sys.exit(1)

    if cd_build_dir:
        print("cd '", str(build[0]).replace("'", "'\\''"), "'", sep="")
    else:
        print(build[0])
