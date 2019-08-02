import argparse

from workspace.bin.util import ws_from_config_name
import workspace.recipes as recipes
from workspace.settings import settings


def main():
    parser = argparse.ArgumentParser(
        description=
        "List all available options with their default values. If given a configuration, only for the recipes appearing in that configuration, otherwise for all available recipes."
    )

    settings.config.add_kwargument(parser)
    settings.recipes.add_argument(parser)
    settings.bind_args(parser)

    recipes_to_list = recipes.ALL
    if settings.recipes.value:
        recipes_to_list = {k: recipes_to_list[k] for k in settings.recipes.value}

    if settings.config.value:
        workspace = ws_from_config_name(settings.config.value)
        for rep in workspace.builds:
            clas = rep.__class__
            name = clas.__name__
            if not name in recipes_to_list:
                continue
            if len(settings.recipes.value) != 1:
                print(f"{name}:")
            clas.list_options(instance=rep)
            print()
    else:
        for (name, clas) in recipes_to_list.items():
            print(f"{name}:")
            clas.list_options()
            print()
