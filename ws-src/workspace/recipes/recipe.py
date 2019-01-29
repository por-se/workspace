import inspect
import enum
from enum import Enum

from workspace.workspace import Workspace

class Recipe:
    def __init__(self, name):
        self.name = name
        self.digest = None

    def initialize(self, ws: Workspace):
        raise NotImplementedError

    def setup(self, ws: Workspace):
        raise NotImplementedError

    def build(self, ws: Workspace):
        raise NotImplementedError

    def add_to_env(self, env, ws: Workspace):
        pass

    def clean(self, ws: Workspace):
        raise NotImplementedError

    @classmethod
    def list_options(cls, instance=None):
        initf = inspect.getargspec(cls.__init__)
        defaults_start = len(initf.args) - len (initf.defaults)
        print(f"Description:\n  {cls.__init__.__doc__}")
        print("Available options:")
        for i in range(1, len(initf.args)): # skip first entry which is always 'self
            argname = initf.args[i]
            set_value = None

            s = f"  '{argname}'"

            if instance and argname in instance.__dict__:
                set_value = instance.__dict__[argname]
                s += f": '{instance.__dict__[argname]}'"

            if i >= defaults_start:
                def_value = initf.defaults[i-defaults_start]
                s += f" (default: '{def_value}')"
            else:
                s += " (required)"

            print(s)

    @staticmethod
    def adjusted_cmake_args(original_args, adjustments):
        """
        Adjust a list of cmake arguments 'original_args', e.g., ['-DFOO=bar', '-DBAR=foo'] with a list of adjustments 'adjustments', e.g., ['-DFOO=BLUB', '-UBAR', '-DNEW=VAL'].
        These adjustment can only contain '-DXXX=yyy' and '-UXXX' entries. Changed entries will be changed, new entries will be appended,
        and '-U'-entries will be removed from the result, which otherwise is a copy of 'original_args'.
        """

        class Mode(enum.Enum):
            DEFINE = 1
            UNDEFINE = 2

        new_args = list(original_args)

        for adj in adjustments:
            if adj.startswith("-D"):
                mode = Mode.DEFINE
                needle = adj[:adj.index("=") + 1]
            elif adj.startswith("-U"):
                mode = Mode.UNDEFINE
                needle = "-D" + adj[2:] + "="
            else:
                raise ValueError(
                    f"adjust_cmake_args: currently only adjustments starting with '-D' or '-U' are possible, but got '{adj}' instead. Please open an issue if required."
                )

            found = False
            for i in range(0, len(new_args)):
                if new_args[i].startswith(needle):
                    found = True
                    if mode == Mode.DEFINE:
                        new_args[i] = adj
                    elif mode == Mode.UNDEFINE:
                        del new_args[i]
                    else:
                        assert False, f"unexpected mode: '{mode}'"
                    break

            if not found and mode == Mode.DEFINE:
                new_args = new_args + [adj]

        return new_args
