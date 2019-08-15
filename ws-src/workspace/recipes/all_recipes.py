from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Type

if TYPE_CHECKING:
    from .recipe import Recipe

ALL: Dict[str, Type[Recipe]] = dict()


def register_recipe(recipe: Type[Recipe]) -> None:
    ALL[recipe.__name__] = recipe
