import argparse

from workspace.bin.util import ws_from_config_name
from workspace.settings import settings


def main():
    parser = argparse.ArgumentParser(description="Setup (usually download sources) one or more configurations.")

    settings.configs.add_argument(parser)
    settings.default_linker.add_kwargument(parser)
    settings.jobs.add_kwargument(parser)
    settings.reference_repositories.add_kwargument(parser)
    settings.until.add_kwargument(parser)
    settings.x_git_clone.add_kwargument(parser)

    settings.bind_args(parser)

    if not settings.configs.value:
        print("Warning: No configurations specified for setup command.")
    elif len(settings.configs.value) == 1:
        print("Setting up", settings.configs.value[0])
        print()
    else:
        print("Setting up", ", ".join(settings.configs.value[:-1]), "and", settings.configs.value[-1])
        print()

    for config in settings.configs.value:
        workspace = ws_from_config_name(config)
        workspace.setup()
