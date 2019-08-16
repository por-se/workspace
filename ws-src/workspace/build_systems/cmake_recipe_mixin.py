from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional

from workspace.build_systems import CMakeConfig

if TYPE_CHECKING:
    import hashlib
    from workspace import Workspace


class CMakeRecipeMixin(abc.ABC):
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
