import abc
from typing import Any, Dict, Mapping


class IRecipe(abc.ABC):
    """
    Interface to individual Recipes.

    If you wish to use a generic recipe, consider using IRecipe.
    If you wish to provide a custom recipe, consider deriving Recipe instead.
    """
    @property
    @abc.abstractmethod
    def name(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def arguments(self) -> Mapping[str, Any]:
        raise NotImplementedError()

    @abc.abstractmethod
    def update_default_arguments(self, default_arguments: Dict[str, Any]) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def update_argument_schema(self, argument_schema: Dict[str, Any]) -> None:
        raise NotImplementedError()
