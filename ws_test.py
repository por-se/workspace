#!/usr/bin/env python3

from workspace_base import Workspace
import workspace_base.recipes as reps

def main():
    ws = Workspace()
    ws.set_builds([
        reps.LLVM("llvm", branch="release_70"),
    ])
    ws.main()

if __name__ == "__main__":
    main()
