import argparse
import shutil

from pyfiglet import Figlet

from workspace import Workspace
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
        pass  # No need to print out a list in advance
    else:
        print("Building", ", ".join(settings.configs.value[:-1]), "and", settings.configs.value[-1])
        print()

    figlet = Figlet(font="doom", width=80)
    for config in settings.configs.value:
        figlet.width = shutil.get_terminal_size(fallback=(9999, 24))[0]
        print(figlet.renderText(f'Building {config}'))
        workspace = Workspace(config)
        workspace.build()
