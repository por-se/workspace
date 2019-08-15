from __future__ import annotations

from typing import TYPE_CHECKING

from cached_property import cached_property

from .vyper import get

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Shell:
    """The shell to invoke (string from choices)"""

    name = "shell"
    choices = ["auto", "bash", "fish", "zsh"]

    def add_kwargument(self, argparser: ArgumentParser, help_message: str = "The shell to invoke"):
        uppercase_name = self.name.upper().replace("-", "_")
        return argparser.add_argument('-s',
                                      '--shell',
                                      choices=self.choices,
                                      help=f'{help_message} (env: WS_{uppercase_name})')

    @cached_property
    def value(self) -> str:
        value = get(self.name)
        if value is None:
            return self.choices[0]
        if value in self.choices:
            return value
        raise Exception(f'value {value} is not valid for setting {self.name}')
