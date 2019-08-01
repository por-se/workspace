from pathlib import Path
from typing import Set

import toml

import workspace.recipes as recipes
from workspace.settings import settings
from workspace.workspace import Workspace


def ws_from_config_name(config_name: str) -> Workspace:
    return ws_from_config_path(settings.ws_path / "ws-config" / f'{config_name}.toml')


def ws_from_config_path(config_path: Path) -> Workspace:
    workspace = Workspace()

    assert config_path, "no config given"
    assert config_path.exists(), f"given config doesn't exist ({config_path})"
    assert not workspace.builds, "build order already defined"

    with open(config_path) as file:
        config = toml.load(file)

    for (target, variations) in config.items():
        if not target in recipes.ALL:
            raise RuntimeError(
                f"no recipe for target '{target}' found (i.e., no class '{target}' in module 'workspace.recipes')")

        seen_names: Set[str] = set()
        for options in variations:
            rep = recipes.ALL[target](**options)

            if rep.name in seen_names:
                raise RuntimeError(f"two variations for target '{target}' with same name '{rep.name}' found")
            seen_names.add(rep.name)

            workspace.builds += [rep]

    return workspace
