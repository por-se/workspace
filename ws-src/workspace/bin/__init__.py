import os
from pathlib import Path

import toml

import workspace.recipes as recipes
from workspace.workspace import Workspace

def get_all_recipes():
    # collect all true subclasses of 'recipes.Recipe' that are in 'recipes'
    # https://stackoverflow.com/questions/7584418/iterate-the-classes-defined-in-a-module-imported-dynamically
    return { name: cls for name, cls in recipes.__dict__.items()
         if isinstance(cls, type) and issubclass(cls, recipes.Recipe)
         and not cls == recipes.Recipe
    }

def available_configs(ws_path):
    available_config_dir = ws_path / 'ws-config' / 'available'
    configs = available_config_dir.glob('*.toml')
    return configs

def resolve_or_default_configs(ws_path, given_configs):
    if given_configs:
        available_config_dir = ws_path / 'ws-config' / 'available'
        configs = [available_config_dir / f"{config}.toml" for config in given_configs]
    else:
        if "WS_ENV_CONFIGURATION" in os.environ:
            available_config_dir = ws_path / 'ws-config' / 'available'
            configs = [
                available_config_dir / f"{os.environ['WS_ENV_CONFIGURATION']}.toml"
            ]
        else:
            active_config_dir = ws_path / 'ws-config' / 'active'
            configs = active_config_dir.glob('*.toml')
    return configs

def ws_path_from_here():
    return Path(__file__).resolve().parent.parent.parent.parent

def ws_from_config(ws_path, config_path):
    ws = Workspace(ws_path)

    assert config_path, "no config given"
    assert config_path.exists(), f"given config doesn't exist ({config_path})"
    assert not ws.builds, "build order already defined"

    with open(config_path) as f:
        config = toml.load(f)

    recipes_to_list = get_all_recipes()

    for (target, variations) in config.items():
        if not target in recipes_to_list:
            raise RuntimeError(
                f"no recipe for target '{target}' found (i.e., no class '{target}' in module 'workspace.recipes')"
            )

        seen_names = set()
        for options in variations:
            rep = recipes_to_list[target](**options)

            if rep.name in seen_names:
                raise RuntimeError(
                    f"two variations for target '{target}' with same name '{rep.name}' found"
                )
            seen_names.update({rep.name})

            ws.builds += [rep]

    return ws
