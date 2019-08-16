from __future__ import annotations

from typing import TYPE_CHECKING

from cached_property import cached_property

from workspace.build_systems.linker import Linker

from .vyper import get

if TYPE_CHECKING:
    from argparse import ArgumentParser


class DefaultLinker:
    """The default linker (workspace.build_systems.Linker)"""

    name = "default-linker"
    choices = [str(linker.value) for linker in Linker]

    def add_kwargument(self, argparser: ArgumentParser, help_message: str = f'The default linker') -> None:
        uppercase_name = self.name.upper().replace("-", "_")
        argparser.add_argument('--default-linker',
                               choices=self.choices,
                               metavar=uppercase_name,
                               help=f'{help_message} (choices: {", ".join(self.choices)}) (env: WS_{uppercase_name})')

    @cached_property
    def value(self) -> Linker:
        value = get(self.name)
        if value is None:
            raise Exception(f'Required property "{self.name}" is not set.')
        assert isinstance(value, str)
        return Linker(value)
