from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from cached_property import cached_property

from .vyper import get
from .ws_path import ws_path

if TYPE_CHECKING:
    from argparse import ArgumentParser

AVAILABLE_CONFIGURATIONS = [path.stem for path in (ws_path / 'ws-config').glob('*.toml')]


class Config:
    """The configuration on which a command is to work on (name of config as string)"""

    name = "config"
    available = AVAILABLE_CONFIGURATIONS
    choices = AVAILABLE_CONFIGURATIONS

    def add_argument(self, argparser: ArgumentParser, help_message: str = f'The chosen configuration') -> None:
        name = self.name
        uppercase_name = self.name.upper().replace("-", "_")
        argparser.add_argument(name,
                               metavar=uppercase_name,
                               nargs="?",
                               choices=self.choices,
                               help=f'{help_message} (choices: {", ".join(self.choices)}) (env: WS_{uppercase_name})')

    def add_kwargument(self, argparser: ArgumentParser, help_message: str = f'The chosen configuration') -> None:
        uppercase_name = self.name.upper().replace("-", "_")
        argparser.add_argument("-c",
                               "--config",
                               metavar=uppercase_name,
                               choices=self.choices,
                               help=f'{help_message} (choices: {", ".join(self.choices)}) (env: WS_{uppercase_name})')

    def _understand_value(self, value: str) -> str:
        if value in self.choices:
            return value
        raise Exception(f'"{value}" is not a valid configuration (encountered while parsing the "{self.name}" setting)')

    @cached_property
    def value(self) -> Optional[str]:
        value = get(self.name)
        if value is None:
            return value
        if isinstance(value, str):
            return self._understand_value(value)
        return self._understand_value(str(value))


class Configs:
    """
    The set of configurations a command is to work on
    (list of configuration names as strings with the additional choice "all" resolved)
    """

    name = "configs"
    available = AVAILABLE_CONFIGURATIONS
    choices = ["all"] + AVAILABLE_CONFIGURATIONS

    def add_argument(self, argparser: ArgumentParser, help_message: str = f'The set of chosen configurations') -> None:
        name = self.name
        uppercase_name = self.name.upper().replace("-", "_")
        # We cannot actually use the choices here, as it effectively turns the nargs="*" into
        # nargs="+", thus disabling the possibility to set this setting from other sources.
        # The default needs to be set to the empty list explicitly, or it will not be seen as "unset".
        argparser.add_argument(name,
                               metavar=uppercase_name,
                               nargs="*",
                               default=[],
                               help=f'{help_message} (choices: {", ".join(self.choices)}) (env: WS_{uppercase_name})')

    def _understand_value(self, value: List[str]) -> List[str]:
        value_set = set(value)
        for config in value_set:
            if config == "all":
                return self.choices[1:]
            if config not in self.choices:
                raise Exception(
                    f'"{config}" is not a valid configuration (encountered while parsing the "{self.name}" setting)')
        return list(value_set)

    @cached_property
    def value(self) -> List[str]:
        value = get(self.name)
        if value is None or value == []:
            value = Config().value
            if value is None:
                return []
            return [value]
        if isinstance(value, list):
            return self._understand_value(value)
        return self._understand_value(str(value).split(","))
