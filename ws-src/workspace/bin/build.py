import argparse

from workspace.bin.util import ws_from_config_name
from workspace.settings import settings


def main():
    parser = argparse.ArgumentParser(
        description="Build one or more configurations. "
        "By default, builds all configurations, or only the configuration of the current environment if one is active.")

    settings.configs.add_argument(parser)
    settings.jobs.add_kwargument(parser)
    settings.until.add_kwargument(parser)

    settings.bind_args(parser)

    if not settings.configs.value:
        print("Warning: No configurations specified for build command.")
    elif len(settings.configs.value) == 1:
        print("Building", settings.configs.value[0])
        print()
    else:
        print("Building", ", ".join(settings.configs.value[:-1]), "and", settings.configs.value[-1])
        print()

    for config in settings.configs.value:
        workspace = ws_from_config_name(config)
        workspace.build()
