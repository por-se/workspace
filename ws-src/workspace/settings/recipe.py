from __future__ import annotations

from typing import TYPE_CHECKING, List

from cached_property import cached_property

from .vyper import get

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Recipes:
    """
    The set of recipes a command is to work on
    (list of recipe names as strings with the additional option "all" resolved)
    """

    name = "recipes"
    choices = ["all"]

    def __init__(self):
        # delayed initialization to give the recipes time to register themselves
        import workspace.recipes.all_recipes
        self.choices = ["all"] + [name for name in workspace.recipes.all_recipes.ALL]

    def add_argument(self, argparser: ArgumentParser, help_message: str = f'The set of chosen recipes'):
        name = self.name
        uppercase_name = self.name.upper().replace("-", "_")
        # We cannot actually use the choices here, as it effectively turns the nargs="*" into
        # nargs="+", thus disabling the possibility to set this setting from other sources.
        # The default needs to be set to the empty list explicitly, or it will not be seen as "unset".
        return argparser.add_argument(
            name,
            metavar=uppercase_name,
            nargs="*",
            default=[],
            help=f'{help_message} (choices: {", ".join(self.choices)}) (env: WS_{uppercase_name})')

    def _understand_value(self, value: List[str]) -> List[str]:
        value_set = set(value)
        for recipe in value_set:
            if recipe == "all":
                return self.choices[1:]
            if recipe not in self.choices:
                raise Exception(
                    f'"{recipe}" is not a valid recipe (encountered while parsing the "{self.name}" setting)')
        return list(value_set)

    @cached_property
    def value(self) -> List[str]:
        value = get(self.name)
        if value is None or value == []:
            return []
        if isinstance(value, list):
            return self._understand_value(value)
        return self._understand_value(str(value).split(","))
