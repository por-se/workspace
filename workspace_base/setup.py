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
			"build = workspace_base:main",
		],
	},
)
