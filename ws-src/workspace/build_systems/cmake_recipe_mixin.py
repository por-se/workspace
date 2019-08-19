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

    def configure(self, workspace: Workspace):
        """
        Override this function to provide custom CMake arguments and settings
        """
        del workspace  # unused parameter

        if "c_flags" in self.profile:
            c_flags = self.profile["c_flags"]
            assert isinstance(c_flags, list)
            for flag in c_flags:
                assert isinstance(flag, str)
            self.cmake.set_extra_c_flags(c_flags)

        if "cxx_flags" in self.profile:
            cxx_flags = self.profile["cxx_flags"]
            assert isinstance(cxx_flags, list)
            for flag in cxx_flags:
                assert isinstance(flag, str)
            self.cmake.set_extra_cxx_flags(cxx_flags)

        if "cmake_args" in self.profile:
            cmake_args = self.profile["cmake_args"]
            assert isinstance(cmake_args, dict)
            for name, value in cmake_args.items():
                assert isinstance(name, str)
                assert isinstance(value, (bool, int, str))
                self.cmake.set_flag(name, value)

    def build_target(self, workspace: Workspace, target=None):
        configure_src_dir = self.paths["configure_src_dir"] if "configure_src_dir" in self.paths else self.paths[
            "src_dir"]
        if not self.cmake.is_configured(workspace, configure_src_dir, self.paths["build_dir"]):
            self.configure(workspace)
            self.cmake.adjust_flags(self.cmake_adjustments)
            self.cmake.configure(workspace, configure_src_dir, self.paths["build_dir"])
        self.cmake.build(workspace, configure_src_dir, self.paths["build_dir"], target=target)

    def build(self, workspace: Workspace):
        self.build_target(workspace)
