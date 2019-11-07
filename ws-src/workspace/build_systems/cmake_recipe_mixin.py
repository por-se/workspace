from __future__ import annotations

import abc
from pathlib import Path
from typing import TYPE_CHECKING, Mapping, Optional, Sequence

from workspace.build_systems import CMakeConfig
from workspace.recipes.irecipe import IRecipe

if TYPE_CHECKING:
    import hashlib
    from workspace import Workspace


class CMakeRecipeMixin(IRecipe, abc.ABC):  # pylint: disable=abstract-method
    __cmake: Optional[CMakeConfig] = None

    def __init__(self, cmake_adjustments: Optional[Sequence[str]] = None):
        self.update_argument_schema({"cmake-adjustments": [str]})
        if cmake_adjustments is None:
            cmake_adjustments = []
        self.update_default_arguments({"cmake-adjustments": cmake_adjustments})

        self._configure_env: Optional[Mapping[str, str]] = None
        self._build_env: Optional[Mapping[str, str]] = None
        self._use_ccache: bool = True
        self._build_targets: Optional[Sequence[str]] = None

    def initialize(self, workspace: Workspace) -> None:
        self.__cmake = CMakeConfig(workspace, self.output_prefix)

        self._configure_env = workspace.get_env()
        self._build_env = workspace.get_env()

    def compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        del workspace  # unused parameter

        for adjustment in self.cmake_adjustments:
            digest.update("CMAKE_ADJUSTMENT_BEGIN".encode())
            digest.update(adjustment.encode())
            digest.update("CMAKE_ADJUSTMENT_END".encode())

    @property
    def cmake_adjustments(self) -> Sequence[str]:
        return self.arguments["cmake-adjustments"]

    @property
    def cmake(self) -> CMakeConfig:
        if self.__cmake is None:
            raise Exception(f'[{self.name}] CMake object requested before it was created')
        return self.__cmake

    def set_build_env(self, env: Mapping[str, str]) -> None:
        self._build_env = env

    def get_build_env(self) -> Mapping[str, str]:
        assert self._build_env, "_build_env must be set (i.e., don't call before 'self.initialize()')"
        return self._build_env

    def set_configure_env(self, env: Mapping[str, str]) -> None:
        self._configure_env = env

    def get_configure_env(self) -> Mapping[str, str]:
        assert self._configure_env, "_configure_env must be set (i.e., don't call before 'self.initialize()')"
        return self._configure_env

    def set_use_ccache(self, use_ccache: bool) -> None:
        self._use_ccache = use_ccache

    def get_use_ccache(self) -> bool:
        return self._use_ccache

    def set_build_targets(self, build_targets: Sequence[str]) -> None:
        self._build_targets = build_targets

    def get_build_targets(self) -> Optional[Sequence[str]]:
        return self._build_targets

    def configure(self, workspace: Workspace) -> None:
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
                assert isinstance(value, (bool, int, str, Path))
                self.cmake.set_flag(name, value)

    def build(self, workspace: Workspace):
        cmake_src_dir = self.paths["cmake_src_dir"] if "cmake_src_dir" in self.paths else self.paths["src_dir"]
        if not self.cmake.is_configured(workspace, cmake_src_dir, self.paths["build_dir"]):
            self.configure(workspace)
            self.cmake.adjust_flags(self.cmake_adjustments)
            self.cmake.configure(workspace,
                                 cmake_src_dir,
                                 self.paths["build_dir"],
                                 env=self.get_configure_env(),
                                 use_ccache=self.get_use_ccache())

        self.cmake.build(workspace,
                         cmake_src_dir,
                         self.paths["build_dir"],
                         targets=self.get_build_targets(),
                         env=self.get_build_env())
