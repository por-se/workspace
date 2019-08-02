import argparse

import workspace.settings


def main():
    parser = argparse.ArgumentParser(description="Resets the settings file to its default content.")
    workspace.settings.settings.bind_args(parser)

    workspace.settings.write_default_settings_file()
