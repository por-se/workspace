from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any, Dict, Type, TypeVar

import schema

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from workspace.workspace import Workspace

R = TypeVar('R', bound="Recipe")  # pylint: disable=invalid-name


class Recipe(abc.ABC):
    default_arguments: Dict[str, Any] = {}

    argument_schema: Dict[str, Any] = {
        "name": str,
    }

    @property
    def name(self) -> str:
        return self.arguments["name"]

    def __init__(self, **kwargs):
        self.arguments = dict(self.default_arguments, **kwargs)
        schema.Schema(self.argument_schema).validate(self.arguments)

        self.digest = None

    def _find_previous_build(self, workspace: Workspace, name: str, typ: Type[R]) -> R:
        build = workspace.find_build(build_name=self.arguments[name], before=self)
        if not build:
            raise Exception(f'[{self.name}] Cannot find build named "{self.arguments[name]}"')
        if not isinstance(build, typ):
            raise Exception(
                f'[{self.name}] The build "{self.arguments[name]}" does not have the required type {typ.__name__}, '
                f'but rather {type(build).__name__}')

        return build

    @abc.abstractmethod
    def initialize(self, workspace: Workspace):
        raise NotImplementedError

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

    @staticmethod
    def concretize_repo_uri(repo_uri, workspace: Workspace):
        for (prefix, replacement) in workspace.get_repository_prefixes().items():
            if repo_uri.startswith(prefix):
                repo_uri = replacement + repo_uri[len(prefix):]
        return repo_uri
