from __future__ import annotations

from typing import TYPE_CHECKING, List

from cached_property import cached_property

from .vyper import get

if TYPE_CHECKING:
    from argparse import ArgumentParser


class XGitClone:
    """Additional arguments to pass to the underlying git clone call (list of strings)"""

    name = "X-git-clone"

    def add_kwargument(self,
                       argparser: ArgumentParser,
                       help_message: str = "Additional arguments to pass to the underlying git clone call") -> None:
        uppercase_name = self.name.upper().replace("-", "_")
        argparser.add_argument('--X-git-clone',
                               metavar=uppercase_name,
                               action="append",
                               help=f'{help_message} (env: WS_{uppercase_name})')

    @cached_property
    def value(self) -> List[str]:
        value = get(self.name)
        if value is None:
            return []

        if isinstance(value, str):
            value = value.split(' ')

        assert isinstance(value, list)
        for element in value:
            assert isinstance(element, str)

        return value
