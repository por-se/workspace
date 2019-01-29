from setuptools import setup, find_packages

setup(
	name = "workspace",
	version = "0.0.1",
	author = "Felix Rath, Daniel Schemmel",
	packages = [
		"workspace",
	],
	entry_points = {
		'console_scripts': [
			"setup        = workspace.bin.setup:main",
            "build        = workspace.bin.build:main",
            "shell        = workspace.bin.shell:main",
            "run          = workspace.bin.run:main",
            "list_options = workspace.bin.list_options:main",
            "clean        = workspace.bin.clean:main",
		],
	},
)
