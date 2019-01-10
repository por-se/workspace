import inspect

from workspace_base.workspace import Workspace

class Recipe:
    def __init__(self, name):
        self.name = name

    def build(self, ws: Workspace):
        raise NotImplementedError

    def add_to_env(self, env, ws: Workspace):
        pass

    def clean(self, ws: Workspace):
        raise NotImplementedError

    @classmethod
    def list_options(cls, setting_dict={}):
        initf = inspect.getargspec(cls.__init__)
        defaults_start = len(initf.args) - len (initf.defaults)
        for i in range(1, len(initf.args)): # skip first entry which is always 'self
            s = f"'{initf.args[i]}'"
            if i >= defaults_start:
                s += f" (default: '{initf.defaults[i-defaults_start]}')"
            else:
                s += " (required)"
            print(s)
