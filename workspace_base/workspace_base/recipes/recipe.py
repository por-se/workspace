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
        print(dir(cls))
