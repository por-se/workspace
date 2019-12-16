from __future__ import annotations

import abc
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Mapping, MutableMapping

if TYPE_CHECKING:
    from workspace import Workspace


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
    def default_name(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def profile_name(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def profile(self) -> Mapping[str, Any]:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def output_prefix(self) -> str:
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

    @property
    @abc.abstractmethod
    def paths(self) -> MutableMapping[str, Path]:
        raise NotImplementedError()

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

    def clean(self, workspace: Workspace):
        """Override `clean` in your recipe, if you need to perform additional cleanup"""
