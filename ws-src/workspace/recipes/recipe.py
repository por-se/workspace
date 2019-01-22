import inspect

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
    def _env_prepend_path(env, key: str, path):
        if key in env and env[key] != "":
            env[key] = f'{path}:{env[key]}'
        else:
            env[key] = f'{path}'
        return env
