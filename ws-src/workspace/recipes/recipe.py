import abc
import inspect

from workspace.workspace import Workspace


class Recipe(abc.ABC):
    def __init__(self, name):
        self.name = name
        self.digest = None

    @abc.abstractmethod
    def initialize(self, workspace: Workspace):
        raise NotImplementedError

    @abc.abstractmethod
    def setup(self, workspace: Workspace):
        raise NotImplementedError

    @abc.abstractmethod
    def build(self, workspace: Workspace):
        raise NotImplementedError

    def add_to_env(self, env, workspace: Workspace):
        pass

    @abc.abstractmethod
    def clean(self, workspace: Workspace):
        raise NotImplementedError

    @classmethod
    def list_options(cls, instance=None):
        initf = inspect.getfullargspec(cls.__init__)
        defaults_start = len(initf.args) - len(initf.defaults)
        print(f"Description:\n  {cls.__init__.__doc__}")
        print("Available options:")
        for i in range(1, len(initf.args)):  # skip first entry which is always 'self
            argname = initf.args[i]

            string = f"  '{argname}'"

            if instance and argname in instance.__dict__:
                string += f": '{instance.__dict__[argname]}'"

            if i >= defaults_start:
                string += f" (default: '{initf.defaults[i - defaults_start]}')"
            else:
                string += " (required)"

            print(string)

    @staticmethod
    def concretize_repo_uri(repo_uri, workspace: Workspace):
        for (prefix, replacement) in workspace.get_repository_prefixes().items():
            if repo_uri.startswith(prefix):
                repo_uri = replacement + repo_uri[len(prefix):]
        return repo_uri
