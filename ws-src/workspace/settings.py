from argparse import ArgumentParser
import multiprocessing
from pathlib import Path
from typing import Optional, List, Dict

from cached_property import cached_property
import toml
from vyper import v

from workspace.build_systems import Linker


class _Settings:
    # get the workspace path
    ws_path: Path = Path(__file__).resolve().parent.parent.parent

    @staticmethod
    def bind_args(argparse: ArgumentParser) -> None:
        v.bind_args(argparse)

    # cached_property requires self, but pylint does not notice it
    # pylint: disable=no-self-use

    @cached_property
    def build_name(self) -> "_BuildName":
        return _BuildName()

    @cached_property
    def config(self) -> "_Config":
        return _Config()

    @cached_property
    def configs(self) -> "_Configs":
        return _Configs()

    @cached_property
    def default_linker(self) -> "_DefaultLinker":
        return _DefaultLinker()

    @cached_property
    def jobs(self) -> "_Jobs":
        return _Jobs()

    @cached_property
    def preserve_settings(self) -> "_PreserveSettings":
        return _PreserveSettings()

    @cached_property
    def recipes(self) -> "_Recipes":
        return _Recipes()

    @cached_property
    def reference_repositories(self) -> "_ReferenceRepositories":
        return _ReferenceRepositories()

    @cached_property
    def shell(self) -> "_Shell":
        return _Shell()

    @cached_property
    def until(self) -> "_Until":
        return _Until()

    @cached_property
    def uri_schemes(self) -> "_UriSchemes":
        return _UriSchemes()

    @cached_property
    def x_git_clone(self) -> "_XGitClone":
        return _XGitClone()

    # pylint: enable=no-self-use


settings = _Settings()  # pylint: disable=invalid-name

#################################################################################

AVAILABLE_CONFIGURATIONS = [path.stem for path in (settings.ws_path / 'ws-config').glob('*.toml')]


class _BuildName:
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


class _Config:
    """The configuration on which a command is to work on (name of config as string)"""

    name = "config"
    available = AVAILABLE_CONFIGURATIONS
    choices = AVAILABLE_CONFIGURATIONS

    def add_argument(self, argparser: ArgumentParser, help_message: str = f'The chosen configuration'):
        name = self.name
        uppercase_name = self.name.upper().replace("-", "_")
        return argparser.add_argument(
            name,
            metavar=uppercase_name,
            nargs="?",
            choices=self.choices,
            help=f'{help_message} (choices: {", ".join(self.choices)}) (env: WS_{uppercase_name})')

    def add_kwargument(self, argparser: ArgumentParser, help_message: str = f'The chosen configuration'):
        uppercase_name = self.name.upper().replace("-", "_")
        return argparser.add_argument(
            "-c",
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


class _Configs:
    """The set of configurations a command is to work on (list of configuration names as strings with the additional choice "all" resolved)"""

    name = "configs"
    available = AVAILABLE_CONFIGURATIONS
    choices = ["all"] + AVAILABLE_CONFIGURATIONS

    def add_argument(self, argparser: ArgumentParser, help_message: str = f'The set of chosen configurations'):
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
            value = settings.config.value
            if value is None:
                return []
            return [value]
        if isinstance(value, list):
            return self._understand_value(value)
        return self._understand_value(str(value).split(","))


class _DefaultLinker:
    """The default linker (workspace.build_systems.Linker)"""

    name = "default-linker"
    choices = [str(linker.value) for linker in Linker]

    def add_kwargument(self, argparser: ArgumentParser, help_message: str = f'The default linker'):
        uppercase_name = self.name.upper().replace("-", "_")
        return argparser.add_argument(
            '--default-linker',
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


class _Jobs:
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


class _PreserveSettings:
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


class _Recipes:
    """The set of recipes a command is to work on (list of recipe names as strings with the additional option "all" resolved)"""

    name = "recipes"
    choices = ["all"]

    def __init__(self):
        import workspace.recipes
        self.choices = ["all"] + [name for name in workspace.recipes.ALL]

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


class _ReferenceRepositories:
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

        return Path(value)

    def update(self, path: str) -> None:
        with open(settings.ws_path / "ws-settings.toml", "r") as file:
            settings_dict = toml.load(file)
        if self.name not in settings_dict or settings_dict[self.name] != path:
            settings_dict[self.name] = path
            with open(settings.ws_path / "ws-settings.toml", "w") as file:
                toml.dump(settings_dict, file)
            v.read_in_config()
            if "value" in self.__dict__:
                del self.value


class _Shell:
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


class _Until:
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


class _UriSchemes:  # pylint: disable=too-few-public-methods
    """The configured extra URI schemas (Dict[str, str])"""

    name = "uri-schemes"

    @cached_property
    def value(self) -> Dict[str, str]:
        value = get(self.name)
        if value is None:
            return {}

        assert isinstance(value, dict)
        for key, val in value.items():
            assert isinstance(key, str)
            assert isinstance(val, str)

        return value


class _XGitClone:
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


#################################################################################

DEFAULT_SETTINGS_FILE = (f'''config = "release"
default-linker = "gold"
preserve-settings = false

[uri-schemes]
"github://" = "ssh://git@github.com/"
"laboratory://" = "ssh://git@laboratory.comsys.rwth-aachen.de/"''')


def write_default_settings_file():
    with open(settings.ws_path / "ws-settings.toml", "w") as file:
        print(DEFAULT_SETTINGS_FILE, file=file)


v.add_config_path(settings.ws_path)
v.set_config_name("ws-settings")
v.set_config_type('toml')
try:
    v.read_in_config()
except FileNotFoundError:
    write_default_settings_file()
    v.read_in_config()

v.set_env_prefix('ws')
v.automatic_env()
v.set_env_key_replacer("-", "_")


def get(key: str):
    # in command line arguments and environment variables, dashes are replaced with underscores
    value = v.get(key.replace("-", "_"))
    if value is None:
        # in the config file, however, they are preserved
        value = v.get(key)
    return value
