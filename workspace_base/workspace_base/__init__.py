import sys
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

    print(config)
    # https://stackoverflow.com/questions/7584418/iterate-the-classes-defined-in-a-module-imported-dynamically
    all_recipes = dict(
        [(name, cls) for name, cls in recipes.__dict__.items()
         if isinstance(cls, type) and issubclass(cls, recipes.Recipe)
         and not cls == recipes.Recipe])

    print(f"all_recipes: {all_recipes}")

    for (target, options) in config.items():
        rep = all_recipes[target](**options)
        ws.builds += [rep]

    return ws


def main():
    ws_path = Path(__file__).resolve().parent.parent.parent
    active_config_dir = ws_path / 'build_configs' / 'active'

    for config in active_config_dir.glob('*.toml'):
        ws = _ws_from_config(ws_path, config)
        ws.main()
