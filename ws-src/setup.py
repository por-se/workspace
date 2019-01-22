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
			"setup = workspace:setup_main",
			"build = workspace:build_main",
            "shell = workspace:shell_main",
            "run = workspace:run_main",
            "list_options = workspace:list_options_main",
            "clean = workspace:clean_main",
		],
	},
)
