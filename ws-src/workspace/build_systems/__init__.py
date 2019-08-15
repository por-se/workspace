from __future__ import annotations

import abc
import shlex
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Set, Union

from .linker import Linker

if TYPE_CHECKING:
    from workspace.workspace import Workspace


def _quote_sequence(seq: Sequence[str]):
    for item in seq:
        yield shlex.quote(item)


class BuildSystemConfig(abc.ABC):
    def __init__(self, workspace: Workspace):
        self.linker = workspace.get_default_linker()

    @abc.abstractmethod
    def is_configured(self, workspace: Workspace, source_dir: Path, build_dir: Path):
        raise NotImplementedError

    @abc.abstractmethod
    def configure(self, workspace: Workspace, source_dir: Path, build_dir: Path):
        raise NotImplementedError

    @abc.abstractmethod
    def build(self, workspace: Workspace, source_dir: Path, build_dir: Path, target=None):
        raise NotImplementedError


class CMakeConfig(BuildSystemConfig):
    class CMakeFlags:
        def __init__(self, flags: Optional[Dict] = None, illegal_flags: Optional[Set] = None):
            self._flags = flags if flags is not None else {}
            self.illegal_flags = illegal_flags if illegal_flags is not None else set()

        def copy(self):
            return CMakeConfig.CMakeFlags(flags=self._flags.copy(), illegal_flags=self.illegal_flags.copy())

        def set(self, name: str, value: Union[str, bool, int], override=True):
            if name in self.illegal_flags:
                raise ValueError(f"changing cmake flag {name} is illegal")
            if override or not name in self._flags:
                self._flags[name] = value

        def unset(self, name: str):
            del self._flags[name]

        def adjust(self, adjustments: List[str]):
            """
            Apply a list of adjustments of the form ['-DFOO=BLUB', '-UBAR', '-DNEW=VAL'] to the currently stored flags.
            These adjustment can only contain '-DXXX=yyy' and '-UXXX' entries. Changed entries will be changed, new
            entries will be appended, and '-U'-entries will be removed from the result, which otherwise is a copy of
            'original_args'.
            """
            for adj in adjustments:
                if adj.startswith("-D"):
                    needle = adj.index("=")
                    name = adj[2:needle]
                    value = adj[needle + 1:]
                    self.set(name, value)
                elif adj.startswith("-U"):
                    name = adj[2:]
                    self.unset(name)
                else:
                    raise ValueError('adjust: currently only adjustments starting with "-D" or "-U" are possible, '
                                     f'but got "{adj}" instead. Please open an issue if required.')

        def generate(self):
            output = []
            for name, value in self._flags.items():
                if isinstance(value, str):
                    value_str = value
                elif isinstance(value, bool):
                    value_str = "ON" if value else "OFF"
                elif isinstance(value, int):
                    value_str = str(value)
                else:
                    raise NotImplementedError(str(type(value)))
                output.append(f"-D{name}={value_str}")
            return output

    def __init__(self, workspace: Workspace):
        super().__init__(workspace)
        self._cmake_flags = CMakeConfig.CMakeFlags(illegal_flags={"CMAKE_C_FLAGS", "CMAKE_CXX_FLAGS"})
        self._extra_c_flags: List[str] = []
        self._extra_cxx_flags: List[str] = []
        self._linker_flags: Optional[Dict[str, List[str]]] = None

    def is_configured(self, workspace: Workspace, source_dir: Path, build_dir: Path):
        return build_dir.exists()

    def configure(self, workspace: Workspace, source_dir: Path, build_dir: Path, env=None):  # pylint: disable=arguments-differ
        assert not self.is_configured(workspace, source_dir, build_dir)

        if not env:
            env = workspace.get_env()

        config_call = ["cmake"]
        config_call += ["-S", str(source_dir), "-B", str(build_dir), "-G", "Ninja"]

        cmake_flags = self._cmake_flags.copy()
        cmake_flags.illegal_flags = set()

        linker_flags = self.get_linker_flags()
        for flags_type, flags in linker_flags.items():
            cmake_flags.set(flags_type, ' '.join(_quote_sequence(flags)))

        cmake_flags.set("CMAKE_C_COMPILER_LAUNCHER", "ccache", override=False)
        cmake_flags.set("CMAKE_CXX_COMPILER_LAUNCHER", "ccache", override=False)

        c_flags = ["-fdiagnostics-color=always", f"-fdebug-prefix-map={str(workspace.ws_path.resolve())}=."]
        if self.linker:
            c_flags.append(f"-B{workspace.get_linker_dir(self.linker)}")
        cxx_flags = c_flags.copy()
        c_flags += self._extra_c_flags
        cxx_flags += self._extra_cxx_flags
        cmake_flags.set("CMAKE_C_FLAGS", ' '.join(_quote_sequence(c_flags)), override=False)
        cmake_flags.set("CMAKE_CXX_FLAGS", ' '.join(_quote_sequence(cxx_flags)), override=False)

        config_call += cmake_flags.generate()

        subprocess.run(config_call, env=env, check=True)

    def build(self, workspace: Workspace, source_dir: Path, build_dir: Path, target=None, env=None):  # pylint: disable=arguments-differ,too-many-arguments
        assert self.is_configured(workspace, source_dir, build_dir)

        from workspace.settings import settings

        if not env:
            env = workspace.get_env()

        build_call = ["cmake", "--build", str(build_dir.resolve()), "-j", str(settings.jobs.value)]
        if target is not None:
            build_call += ['--target', target]

        subprocess.run(build_call, env=env, check=True)

    def set_flag(self, name: str, value: Union[str, bool, int]):
        self._cmake_flags.set(name, value)

    def unset_flag(self, name: str):
        self._cmake_flags.unset(name)

    def adjust_flags(self, flags: List[str]):
        self._cmake_flags.adjust(flags)

    def set_extra_c_flags(self, flags: List[str]):
        self._extra_c_flags = flags

    def set_extra_cxx_flags(self, flags: List[str]):
        self._extra_cxx_flags = flags

    def force_linker_flags(self, flags: Optional[Dict[str, List[str]]]):
        self._linker_flags = flags

    def get_linker_flags(self):
        if self._linker_flags is not None:
            return self._linker_flags
        if self.linker in [Linker.GOLD, Linker.LLD]:
            return {
                "CMAKE_STATIC_LINKER_FLAGS": ["-T"],
                "CMAKE_MODULE_LINKER_FLAGS": ["-Xlinker", "--no-threads"],
                "CMAKE_SHARED_LINKER_FLAGS": ["-Xlinker", "--no-threads"],
                "CMAKE_EXE_LINKER_FLAGS": ["-Xlinker", "--no-threads", "-Xlinker", "--gdb-index"]
            }
        if self.linker == Linker.LD:
            return {
                "CMAKE_STATIC_LINKER_FLAGS": ["-T"],
                "CMAKE_MODULE_LINKER_FLAGS": [],
                "CMAKE_SHARED_LINKER_FLAGS": [],
                "CMAKE_EXE_LINKER_FLAGS": []
            }
        raise NotImplementedError(str(self.linker))
