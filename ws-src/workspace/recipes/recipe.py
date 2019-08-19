from __future__ import annotations

import abc
import hashlib
from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional, Type, TypeVar

import schema
from base58 import b58encode

from .irecipe import IRecipe

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from workspace import Workspace

R = TypeVar('R', bound="Recipe")  # pylint: disable=invalid-name


class Recipe(IRecipe, abc.ABC):
    """
    Abstract base class for recipes.

    If you wish to provide a custom recipe, consider deriving Recipe.
    If you wish to use a generic recipe, consider using IRecipe instead.
    """

    default_arguments: Dict[str, Any] = {}
    argument_schema: Dict[str, Any] = {}
    profiles: Dict[str, Dict[str, Any]] = {"default": {}}

    def update_default_arguments(self, default_arguments: Dict[str, Any]) -> None:
        self.default_arguments.update(default_arguments)

    def update_argument_schema(self, argument_schema: Dict[str, Any]) -> None:
        self.argument_schema.update(argument_schema)

    @property
    def arguments(self) -> Mapping[str, Any]:
        return self.__arguments

    @property
    def name(self) -> str:
        result = self.arguments["name"]
        assert isinstance(result, str)
        return result

    @property
    def default_name(self) -> str:
        result = self.default_arguments["name"]
        assert isinstance(result, str)
        return result

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
        """
        Call the Recipe `__init__` once all `default_arguments` and `argument_schema`s are set up and pass in the actual
        arguments. This is typically the case after calling `__init__` on all Mixins.
        """

        default_arguments = {"name": type(self).__name__.lower().replace("_", "-")}
        if "default" in self.profiles:
            default_arguments["profile"] = "default"
        self.default_arguments = dict(default_arguments, **self.default_arguments)
        self.__arguments = dict(self.default_arguments, **kwargs)
        self.argument_schema = dict({"name": str, "profile": schema.Or(*self.profiles.keys())}, **self.argument_schema)

    def __validate(self):
        try:
            schema.Schema(self.argument_schema).validate(self.arguments)
        except schema.SchemaError as error:
            raise Exception(f'[{self.name}] Could not validate configuration: {error}')

    @property
    def profile_name(self) -> str:
        result = self.arguments["profile"]
        if not result or not isinstance(result, str):
            raise Exception(f'[{self.name}] Could not acquire current profile')
        return result

    @property
    def profile(self) -> Mapping[str, Any]:
        return self.profiles[self.profile_name]

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
        """Override `initialize` in your recipe, but call the base version in the beginning"""
        self.__validate()

        digest = hashlib.blake2s()
        self.compute_digest(workspace, digest)
        self.__digest = digest.digest()

    def compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        """Override `compute_digest` in your recipe, but call the base version in the beginning"""
        del workspace  # unused parameter

        digest.update(self.name.encode())
        digest.update(self.profile_name.encode())

    @abc.abstractmethod
    def setup(self, workspace: Workspace):
        """Override `setup` in your recipe, to check out repositories, prepare code, etc."""
        raise NotImplementedError

    @abc.abstractmethod
    def build(self, workspace: Workspace):
        """Override `build` in your recipe, to build the recipe"""
        raise NotImplementedError

    def add_to_env(self, env, workspace: Workspace):
        """
        Override `add_to_env` in your recipe, to set up the environment that allows your build artifacts to be used
        """

        pass

    def clean(self, workspace: Workspace):
        """Override `clean` in your recipe, if you need to perform additional cleanup"""
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

        self = instance if instance is not None else cls()

        print(f'Description:\n  {cleandoc(cls.__doc__) if cls.__doc__ else ""}')
        print("Available options:")
        for argument, typ in self.argument_schema.items():
            print(f'  {argument}: ', end="")
            Recipe.__print_schema_type(typ)

            if instance and argument in instance.arguments:
                print(f' = {instance.arguments[argument]!r}', end="")

            if argument in self.default_arguments:
                print(f" (defaults to {self.default_arguments[argument]!r})", end="")
            else:
                print(" (required)", end="")

            print()
