import sys, os
from pathlib import Path
from pprint import pprint

import toml

import workspace_base.recipes
from workspace_base.workspace import Workspace
from .workspace import Workspace


def _ws_from_config(ws_path, config_path):
    print(f".. loading config: {config_path}")

    ws = Workspace(ws_path)

    assert config_path, "no config given"
    assert config_path.exists(), f"given config doesn't exist ({config_path})"
    assert not ws.builds, "build order already defined"

    with open(config_path) as f:
        config = toml.load(f)

    # collect all true subclasses of 'recipes.Recipe' that are in 'recipes'
    # https://stackoverflow.com/questions/7584418/iterate-the-classes-defined-in-a-module-imported-dynamically
    all_recipes = dict(
        [(name, cls) for name, cls in recipes.__dict__.items()
         if isinstance(cls, type) and issubclass(cls, recipes.Recipe)
         and not cls == recipes.Recipe])

    for (target, variations) in config.items():
        if not target in all_recipes:
            raise RuntimeError(
                f"no recipe for target '{target}' found (i.e., no class '{target}' in module 'workspace_base.recipes')"
            )

        seen_names = set()
        for options in variations:
            rep = all_recipes[target](**options)

            if rep.name in seen_names:
                raise RuntimeError(
                    f"two variations for target '{target}' with same name '{rep.name}' found"
                )
            seen_names.update({rep.name})

            ws.builds += [rep]

    return ws


def main():
    ws_path = Path(__file__).resolve().parent.parent.parent

    if "WS_ENV_CONFIGURATION" in os.environ:
        available_config_dir = ws_path / 'build_configs' / 'available'
        configs = [available_config_dir / f"{os.environ['WS_ENV_CONFIGURATION']}.toml"]
    else:
        active_config_dir = ws_path / 'build_configs' / 'active'
        configs = active_config_dir.glob('*.toml')

    for config in configs:
        ws = _ws_from_config(ws_path, config)
        ws.main()
