from __future__ import annotations

import abc
import hashlib
from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional, Type, TypeVar

import schema
from base58 import b58encode

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from workspace import Workspace

R = TypeVar('R', bound="Recipe")  # pylint: disable=invalid-name


class Recipe(abc.ABC):
    default_arguments: Dict[str, Any] = {}
    argument_schema: Dict[str, Any] = {}

    def update_default_arguments(self, default_arguments: Dict[str, Any]) -> None:
        self.default_arguments.update(default_arguments)

    def update_argument_schema(self, argument_schema: Dict[str, Any]) -> None:
        self.argument_schema.update(argument_schema)

    @property
    def arguments(self) -> Mapping[str, Any]:
        return self.__arguments

    @property
    def name(self) -> str:
        return self.arguments["name"]

    __digest: Optional[bytes] = None

    @property
    def digest(self) -> bytes:
        if not self.__digest:
            raise Exception(f'[{self.name}] Digest requested before it was computed')
        return self.__digest

    @property
    def digest_str(self) -> str:
        return b58encode(self.digest).decode("utf-8")[:16]  # slightly more than 41 chars would be available (blake2s)

    def __init__(self, **kwargs):
        self.__arguments = dict(self.default_arguments, **kwargs)
        argument_schema = dict({"name": str}, **self.argument_schema)
        try:
            schema.Schema(argument_schema).validate(self.arguments)
        except schema.SchemaError as error:
            raise Exception(f'[{self.name}] Could not validate configuration: {error}')

    def _find_previous_build(self, workspace: Workspace, name: str, typ: Type[R]) -> R:
        build = workspace.find_build(build_name=self.arguments[name], before=self)
        if not build:
            raise Exception(f'[{self.name}] Cannot find build named "{self.arguments[name]}"')
        if not isinstance(build, typ):
            raise Exception(
                f'[{self.name}] The build "{self.arguments[name]}" does not have the required type {typ.__name__}, '
                f'but rather {type(build).__name__}')

        return build

    def initialize(self, workspace: Workspace) -> None:
        digest = hashlib.blake2s()
        self.compute_digest(workspace, digest)
        self.__digest = digest.digest()

    def compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        del workspace

        digest.update(self.name.encode())

    @abc.abstractmethod
    def setup(self, workspace: Workspace):
        raise NotImplementedError

    @abc.abstractmethod
    def build(self, workspace: Workspace):
        raise NotImplementedError

    def add_to_env(self, env, workspace: Workspace):
        pass

    def clean(self, workspace: Workspace):
        pass

    @staticmethod
    def __print_schema_or(obj: schema.Or):
        optional = False
        elements = []
        for element in obj._args:  # pylint: disable=protected-access
            if element is None:
                optional = True
            else:
                elements.append(element)
        assert elements

        if len(elements) > 1:
            print("(", end="")
        for i, element in enumerate(elements):  # pylint: disable=protected-access
            if i > 0:
                print("|", end="")
            Recipe.__print_schema_type(element)
        if len(elements) > 1:
            print(")", end="")
        if optional:
            print("?", end="")

    @staticmethod
    def __print_schema_type(obj):
        if isinstance(obj, type):
            print(obj.__name__, end="")
        elif isinstance(obj, list):
            print("[", end="")
            for i, element in enumerate(obj):
                if i > 0:
                    print(", ", end="")
                Recipe.__print_schema_type(element)
            print("]", end="")
        elif isinstance(obj, schema.Or):
            Recipe.__print_schema_or(obj)
        elif isinstance(obj, str):
            print(f'{obj!r}', end="")
        else:
            assert False, f'Missing case: {type(obj)} not implemented'

    @classmethod
    def list_options(cls, instance=None):
        from inspect import cleandoc

        print(f'Description:\n  {cleandoc(cls.__doc__) if cls.__doc__ else ""}')
        print("Available options:")
        for argument, typ in cls.argument_schema.items():  # skip first entry which is always 'self
            print(f'  {argument}: ', end="")
            Recipe.__print_schema_type(typ)

            if instance and argument in instance.arguments:
                print(f' = {instance.arguments[argument]!r}', end="")

            if argument in cls.default_arguments:
                print(f" (defaults to {cls.default_arguments[argument]!r})", end="")
            else:
                print(" (required)", end="")

            print()
