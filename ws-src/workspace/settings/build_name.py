from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from cached_property import cached_property

from .vyper import get

if TYPE_CHECKING:
    from argparse import ArgumentParser


class BuildName:
    """The name of the chosen build (unvalidated string)"""

    name = "build-name"

    def add_argument(self, argparser: ArgumentParser, help_message: str = f'The name of the chosen build') -> None:
        name = self.name
        uppercase_name = self.name.upper().replace("-", "_")
        argparser.add_argument(name,
                               metavar=uppercase_name,
                               nargs="?",
                               help=f'{help_message} (env: WS_{uppercase_name})')

    @cached_property
    def value(self) -> Optional[str]:
        value = get(self.name)
        if value is None:
            return None
        if isinstance(value, str):
            return value
        raise Exception(f'value {value} is not valid for setting {self.name}')
