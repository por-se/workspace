from pathlib import Path
from typing import Any, Set

import toml

import workspace.recipes as recipes
from workspace.settings import settings
from workspace.workspace import Workspace


def ws_from_config_name(config_name: str) -> Workspace:
    return ws_from_config_path(settings.ws_path / "ws-config" / f'{config_name}.toml')


def validate_config(config: Any) -> None:
    from schema import Schema, Or

    Schema({"Recipe": [{"recipe": Or(*recipes.ALL.keys()), str: object}]}).validate(config)


def ws_from_config_path(config_path: Path) -> Workspace:
    workspace = Workspace()

    assert config_path, "no config given"
    assert config_path.exists(), f"given config doesn't exist ({config_path})"
    assert not workspace.builds, "build order already defined"

    with open(config_path) as file:
        config = toml.load(file)
    validate_config(config)
    items = config["Recipe"]
    if not items:
        raise Exception(f'The configuration at location "{config_path}" is empty.')

    seen_names: Set[str] = set()
    for item in items:
        options = dict(item)  # shallow copy
        del options["recipe"]
        rep = recipes.ALL[item["recipe"]](**options)

        if rep.name in seen_names:
            raise RuntimeError(
                f'two recipe variations with same name "{rep.name}"" found in configuration at location "{config_path}"'
            )
        seen_names.add(rep.name)

        workspace.builds += [rep]

        if rep.name == settings.until.value:
            break

    if settings.until.value and settings.until.value not in seen_names:
        raise Exception(
            f'The configuration at location "{config_path}" does not contain a build named "{settings.until.value}" which should terminate processing.'
        )

    return workspace
