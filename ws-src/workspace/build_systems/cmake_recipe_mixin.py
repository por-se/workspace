from __future__ import annotations

import abc
from typing import TYPE_CHECKING, List, Optional

from workspace.build_systems import CMakeConfig
from workspace.recipes.irecipe import IRecipe

if TYPE_CHECKING:
    import hashlib
    from workspace import Workspace


class CMakeRecipeMixin(IRecipe, abc.ABC):  # pylint: disable=abstract-method
    def __init__(self, cmake_adjustments: Optional[List[str]] = None):
        self.update_argument_schema({"cmake-adjustments": [str]})

        if cmake_adjustments is None:
            cmake_adjustments = []
        self.update_default_arguments({"cmake-adjustments": cmake_adjustments})

    def initialize(self, workspace: Workspace) -> None:
        self.__cmake = CMakeConfig(workspace)

    def compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        del workspace  # unused parameter

        for adjustment in self.cmake_adjustments:
            digest.update("CMAKE_ADJUSTMENT_BEGIN".encode())
            digest.update(adjustment.encode())
            digest.update("CMAKE_ADJUSTMENT_END".encode())

    @property
    def cmake_adjustments(self) -> List[str]:
        return self.arguments["cmake-adjustments"]

    __cmake: Optional[CMakeConfig] = None

    @property
    def cmake(self) -> CMakeConfig:
        if self.__cmake is None:
            raise Exception(f'[{self.name}] CMake object requested before it was created')
        return self.__cmake
