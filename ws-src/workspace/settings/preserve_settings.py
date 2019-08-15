from __future__ import annotations

from typing import TYPE_CHECKING

from cached_property import cached_property

from .vyper import get

if TYPE_CHECKING:
    from argparse import ArgumentParser


class PreserveSettings:
    """Preserve ws-settings.toml on dist-clean (boolean)"""

    name = "preserve-settings"

    def add_kwargument(self, argparser: ArgumentParser, help_message: str = "Preserve ws-settings.toml"):
        uppercase_name = self.name.upper().replace("-", "_")
        return argparser.add_argument('-p',
                                      '--preserve-settings',
                                      action='store_const',
                                      const=True,
                                      help=f'{help_message} (env: WS_{uppercase_name})')

    @cached_property
    def value(self) -> bool:
        value = get(self.name)
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if value == "1" or value.upper() == "TRUE":
            return True
        if value == "0" or value.upper() == "FALSE":
            return False
        raise Exception(f'value {value} is not valid for setting {self.name}')
