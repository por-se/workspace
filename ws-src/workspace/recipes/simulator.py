from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

import schema

from workspace.build_systems.cmake_recipe_mixin import CMakeRecipeMixin
from workspace.settings import settings
from workspace.util import env_prepend_path
from workspace.vcs.git import GitRecipeMixin

from .all_recipes import register_recipe
from .recipe import Recipe

if TYPE_CHECKING:
    import hashlib
    from .porse import PORSE
    from workspace import Workspace


class SIMULATOR(Recipe, GitRecipeMixin, CMakeRecipeMixin):  # pylint: disable=invalid-name
    """The libpor and simulator for PORSE"""

    profiles = {
        "release": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Release',
            },
        },
        "rel+debinfo": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'RelWithDebInfo',
            },
            "cxx_flags":
            ["-fno-omit-frame-pointer", "-g3", "-fvar-tracking", "-fvar-tracking-assignments", "-fdebug-types-section"],
        },
        "debug": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Debug',
            },
            "cxx_flags":
            ["-fno-omit-frame-pointer", "-g3", "-fvar-tracking", "-fvar-tracking-assignments", "-fdebug-types-section"],
        },
        "sanitized": {
            "cmake_args": {
                'CMAKE_BUILD_TYPE': 'Asan',
            },
        },
    }

    default_arguments: Dict[str, Any] = {
        "porse": None,
        "verified-fingerprints": False,
    }

    argument_schema: Dict[str, Any] = {
        "porse": schema.Or(str, None),
        "verified-fingerprints": bool,
    }

    def find_porse(self, workspace: Workspace) -> Optional[PORSE]:
        if self.porse is None:
            return None
        return workspace.find_build(self.porse, before=None)

    @property
    def porse(self) -> Optional[str]:
        return self.arguments["porse"]

    @property
    def verified_fingerprints(self) -> bool:
        return self.arguments["verified-fingerprints"]

    def __init__(self, **kwargs):
        GitRecipeMixin.__init__(self, "laboratory://symbiosys/projects/concurrent-symbolic-execution/simulator.git")
        CMakeRecipeMixin.__init__(self)
        Recipe.__init__(self, **kwargs)

    def initialize(self, workspace: Workspace):
        Recipe.initialize(self, workspace)
        CMakeRecipeMixin.initialize(self, workspace)

        porse = self.find_porse(workspace)
        if porse:
            if self.name != porse.simulator:
                raise Exception(f'[{self.name}] The {porse.__class__.__name__} build named "{porse.name}" '
                                f'must use the {self.__class__.__name__} build named "{self.name}"')

            if self.verified_fingerprints != porse.verified_fingerprints:
                raise Exception(f'[{self.name}] The {porse.__class__.__name__} build named "{porse.name}" '
                                f'and the {self.__class__.__name__} build named "{self.name}" must have the same '
                                f'verified fingerprints settings')

    def compute_digest(self, workspace: Workspace, digest: "hashlib._Hash") -> None:
        Recipe.compute_digest(self, workspace, digest)
        CMakeRecipeMixin.compute_digest(self, workspace, digest)

        porse = self.find_porse(workspace)
        if porse:
            # porse include dir is known at this time as it does not depend on the digest
            # and is independent of build arguments for the porse recipe
            digest.update(f'porse-include-dir:{porse.paths["include_dir"].relative_to(settings.ws_path)}'.encode())
            digest.update(f'verified-fingerprints:{self.verified_fingerprints}'.encode())

    def configure(self, workspace: Workspace):
        CMakeRecipeMixin.configure(self, workspace)

        porse = self.find_porse(workspace)
        if porse:
            self.cmake.set_flag('KLEE_INCLUDE_DIR', porse.paths["include_dir"])
            self.cmake.set_flag('KLEE_VERIFIED_FINGERPRINTS', self.verified_fingerprints)

    def add_to_env(self, env, workspace: Workspace):
        env_prepend_path(env, "PATH", self.paths["build_dir"] / "bin" / "random-graph")


register_recipe(SIMULATOR)
