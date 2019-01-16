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
			"build = workspace:build_main",
            # do NOT name this 'env', as it will override the shell-builtin 'env'!
            "into_env = workspace:env_main",
            "list_options = workspace:list_options_main",
            "clean = workspace:clean_main",
		],
	},
)
