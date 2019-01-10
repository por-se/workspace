from setuptools import setup, find_packages

setup(
	name = "workspace_base",
	version = "0.0.1",
	author = "Felix Rath, Daniel Schemmel",
	packages = [
		"workspace_base",
	],
	entry_points = {
		'console_scripts': [
			"build = workspace_base:build_main",
            # do NOT name this 'env', as it will override the shell-builtin 'env'!
            "into_env = workspace_base:env_main",
            "list_options = workspace_base:list_options_main",
            "clean = workspace_base:clean_main",
		],
	},
)
