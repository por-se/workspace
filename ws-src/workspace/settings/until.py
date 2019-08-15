from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from cached_property import cached_property

from .vyper import get

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Until:
    """Abort processing after the given build name (build name as string)"""

    name = "until"

    def add_kwargument(self,
                       argparser: ArgumentParser,
                       help_message: str = f'Abort processing after the given build name'):
        uppercase_name = self.name.upper().replace("-", "_")
        return argparser.add_argument('-u', '--until', help=f'{help_message} (env: WS_{uppercase_name})')

    @cached_property
    def value(self) -> Optional[str]:
        value = get(self.name)
        if value is None:
            return None
        if isinstance(value, str):
            return value
        raise Exception(f'value {value} is not valid for setting {self.name}')
