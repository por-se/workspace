from workspace.workspace import Workspace
from workspace.bin.util import ws_path_from_here

def main():
    ws_path = ws_path_from_here()
    ws = Workspace(ws_path)
    ws.reset_config();
