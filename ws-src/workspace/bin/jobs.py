import argparse

from workspace.settings import settings


def main():
    parser = argparse.ArgumentParser(description="Print the number of jobs that a real command would have used.")
    settings.jobs.add_kwargument(parser)
    settings.bind_args(parser)

    print(settings.jobs.value)
