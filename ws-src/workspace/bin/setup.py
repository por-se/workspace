import argparse
import shutil

from pyfiglet import Figlet

from workspace import Workspace
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
        pass  # No need to print out a list in advance
    else:
        print("Setting up", ", ".join(settings.configs.value[:-1]), "and", settings.configs.value[-1])
        print()

    figlet = Figlet(font="doom", width=80)
    for config in settings.configs.value:
        figlet.width = shutil.get_terminal_size(fallback=(9999, 24))[0]
        print(figlet.renderText(f'Setting up {config}'))
        workspace = Workspace(config)
        workspace.setup()
