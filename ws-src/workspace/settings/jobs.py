from __future__ import annotations

from typing import TYPE_CHECKING

from cached_property import cached_property

from .vyper import get

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Jobs:
    """The number of parallel jobs to start (int > 0 with 0 resolved as the number of CPUs)"""

    name = "jobs"

    def add_kwargument(self, argparser: ArgumentParser, help_message: str = "The number of parallel jobs to start"):
        uppercase_name = self.name.upper().replace("-", "_")
        return argparser.add_argument('-j',
                                      '--jobs',
                                      metavar=uppercase_name,
                                      help=f'{help_message} (env: WS_{uppercase_name})')

    @cached_property
    def value(self) -> int:
        import multiprocessing

        value = get(self.name)
        if value is None:
            value = 0
        else:
            value = int(value)

        if value == 0:
            value = multiprocessing.cpu_count()
        elif value < 0 or value >= 1000:
            raise Exception(f'"{value}" is out of range for the "{self.name}" setting')
        return value
