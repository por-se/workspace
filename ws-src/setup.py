from setuptools import setup

setup(
    name="workspace",
    version="0.0.1",
    author="Felix Rath, Daniel Schemmel",
    packages=[
        "workspace",
    ],
    entry_points={
        'console_scripts': [
            "setup          = workspace.bin.setup:main",
            "reset-settings = workspace.bin.reset_settings:main",
            "build          = workspace.bin.build:main",
            "activate-cfg   = workspace.bin.activate_cfg:main",
            "deactivate-cfg = workspace.bin.deactivate_cfg:main",
            "shell          = workspace.bin.shell:main",
            "run            = workspace.bin.run:main",
            "build-dir      = workspace.bin.build_dir:main",
            "list-options   = workspace.bin.list_options:main",
            "clean          = workspace.bin.clean:main",
            "dist-clean     = workspace.bin.dist_clean:main",
            "_ws_jobs       = workspace.bin.jobs:main",
            "_ws_nop        = workspace.bin.nop:main",
        ],
    },
)
