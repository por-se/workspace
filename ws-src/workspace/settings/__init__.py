from __future__ import annotations

from argparse import ArgumentParser
from typing import TYPE_CHECKING

from cached_property import cached_property
from vyper import v

from .build_name import BuildName
from .config import Config, Configs
from .default_linker import DefaultLinker
from .jobs import Jobs
from .preserve_settings import PreserveSettings
from .recipe import Recipes
from .reference_repositories import ReferenceRepositories
from .shell import Shell
from .until import Until
from .uri_schemes import UriSchemes
from .vyper import get, write_default_settings_file
from .ws_path import ws_path
from .x_git_clone import XGitClone

if TYPE_CHECKING:
    from pathlib import Path

__all__ = [
    "get",
    "write_default_settings_file",
    "settings",
]


class _Settings:
    def __init__(self) -> None:
        # get the workspace path
        self.ws_path: Path = ws_path

    @staticmethod
    def bind_args(argparse: ArgumentParser) -> None:
        v.bind_args(argparse)

    # cached_property requires self, but pylint does not notice it
    # pylint: disable=no-self-use

    @cached_property
    def build_name(self) -> BuildName:
        return BuildName()

    @cached_property
    def config(self) -> Config:
        return Config()

    @cached_property
    def configs(self) -> Configs:
        return Configs()

    @cached_property
    def default_linker(self) -> DefaultLinker:
        return DefaultLinker()

    @cached_property
    def jobs(self) -> Jobs:
        return Jobs()

    @cached_property
    def preserve_settings(self) -> PreserveSettings:
        return PreserveSettings()

    @cached_property
    def recipes(self) -> Recipes:
        return Recipes()

    @cached_property
    def reference_repositories(self) -> ReferenceRepositories:
        return ReferenceRepositories()

    @cached_property
    def shell(self) -> Shell:
        return Shell()

    @cached_property
    def until(self) -> Until:
        return Until()

    @cached_property
    def uri_schemes(self) -> UriSchemes:
        return UriSchemes()

    @cached_property
    def x_git_clone(self) -> XGitClone:
        return XGitClone()

    # pylint: enable=no-self-use


settings = _Settings()  # pylint: disable=invalid-name
