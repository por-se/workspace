from workspace_base.workspace import Workspace

class Recipe:
    def __init__(self, name):
        self.name = name

    def build(self, ws: Workspace):
        raise NotImplementedError

    def clean(self, ws: Workspace):
        raise NotImplementedError
