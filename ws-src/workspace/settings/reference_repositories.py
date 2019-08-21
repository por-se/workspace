from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

import toml
from cached_property import cached_property
from vyper import v

from .vyper import get
from .ws_path import ws_path

if TYPE_CHECKING:
    from argparse import ArgumentParser


class ReferenceRepositories:
    """The location of the reference repositories (Path)"""

    name = "reference-repositories"

    def add_kwargument(self,
                       argparser: ArgumentParser,
                       help_message: str = "The location of the reference repositories") -> None:
        uppercase_name = self.name.upper().replace("-", "_")
        argparser.add_argument('--reference-repositories',
                               metavar=uppercase_name,
                               help=f'{help_message} (env: WS_{uppercase_name})')

    @cached_property
    def value(self) -> Optional[Path]:
        value = get(self.name)
        if value is None:
            return value

        return Path(value).resolve()

    def update(self, path: Union[str, Path]) -> None:
        if isinstance(path, Path):
            path = str(path.resolve())
        with open(ws_path / "ws-settings.toml", "r") as file:
            settings_dict = toml.load(file)
        if self.name not in settings_dict or settings_dict[self.name] != path:
            settings_dict[self.name] = path
            with open(ws_path / "ws-settings.toml", "w") as file:
                toml.dump(settings_dict, file)
            v.read_in_config()
            if "value" in self.__dict__:
                del self.value
