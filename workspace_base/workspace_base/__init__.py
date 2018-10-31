import sys

from pathlib import Path

from .workspace import Workspace

def main():
    ws = Workspace(Path(__file__).resolve().parent.parent.parent)
    ws.main()
