import abc
import inspect
import enum
from enum import Enum

from workspace.workspace import Workspace

class Recipe(abc.ABC):
    def __init__(self, name):
        self.name = name
        self.digest = None

    @abc.abstractmethod
    def initialize(self, ws: Workspace):
        raise NotImplementedError

    @abc.abstractmethod
    def setup(self, ws: Workspace):
        raise NotImplementedError

    @abc.abstractmethod
    def build(self, ws: Workspace):
        raise NotImplementedError

    def add_to_env(self, env, ws: Workspace):
        pass

    @abc.abstractmethod
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
    def concretize_repo_uri(repo_uri, ws: Workspace):
        for (prefix,replacement) in ws.get_repository_prefixes().items():
            if repo_uri.startswith(prefix):
                repo_uri = replacement + repo_uri[len(prefix):]
        return repo_uri

