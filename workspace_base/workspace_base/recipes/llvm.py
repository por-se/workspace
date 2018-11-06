from workspace_base.workspace import Workspace
from . import Recipe

from pathlib import Path

class LLVM(Recipe):
    def __init__(self, branch, profile, name="llvm"):
        super().__init__(name)
        self.branch = branch

    def build(self, ws: Workspace):
        local_repo_path = ws.ws_path / self.name

        if not local_repo_path.is_dir():
            ws.reference_clone(
                "https://llvm.org/git/llvm",
                target_path=local_repo_path,
                branch=self.branch)
            ws.apply_patches("llvm", local_repo_path)

        test_suite_path = local_repo_path / 'projects/test-suite'
        if not test_suite_path.is_dir():
            ws.reference_clone(
                "https://llvm.org/git/llvm",
                target_path=test_suite_path,
                branch=self.branch)
            ws.apply_patches("llvm-test-suite", test_suite_path)

        clang_path = local_repo_path / 'tools/clang'
        if not clang_path.is_dir():
            ws.reference_clone(
                "https://llvm.org/git/clang",
                target_path=clang_path,
            branch=self.branch)
            ws.apply_patches("clang", clang_path)

        raise NotImplementedError
