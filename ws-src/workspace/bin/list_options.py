import argparse, os
from workspace.bin.util import get_all_recipes, ws_path_from_here, ws_from_config

def main():
    parser = argparse.ArgumentParser(
        description=
        "List all available options with their default values. If given a configuration, only for the recipes appearing in that configuration, otherwise for all available recipes."
    )

    parser.add_argument(
        'recipes',
        metavar='recipe',
        type=str,
        nargs='*',
        help="The recipes for which to print options")

    parser.add_argument(
        '-c',
        '--config',
        type=str,
        default=None,
        help="specify the configuration for which to print options")

    args = parser.parse_args()

    ws_path = ws_path_from_here()

    if args.config:
        available_config_dir = ws_path / 'ws-config'
        config = available_config_dir / f"{args.config}.toml"
    elif "WS_ENV_CONFIGURATION" in os.environ:
        available_config_dir = ws_path / 'ws-config'
        config = available_config_dir / f"{os.environ['WS_ENV_CONFIGURATION']}.toml"
    else:
        config = None

    recipes_to_list = get_all_recipes()
    if args.recipes:
        recipes_to_list = {k: recipes_to_list[k] for k in args.recipes}

    if config:
        ws = ws_from_config(ws_path, config)
        for rep in ws.builds:
            clas = rep.__class__
            name = clas.__name__
            if not name in recipes_to_list:
                continue
            print(f"{name}:")
            clas.list_options(instance=rep)
            print()
    else:
        for (name, clas) in recipes_to_list.items():
            print(f"{name}:")
            clas.list_options()
            print()
