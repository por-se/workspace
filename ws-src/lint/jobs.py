#!/usr/bin/env python3

import argparse
import os
import sys
from multiprocessing import cpu_count
from pathlib import Path
from typing import Optional

import toml


def understand_jobs(jobs: int, context: str) -> int:
    if jobs < 0 or jobs >= 1000:
        print(f'The jobs value {jobs} {context} is outside the valid range [0; 1000).', file=sys.stderr)
        sys.exit(2)
    if jobs == 0:
        return cpu_count()
    return jobs


def parse_jobs(jobs: str, context: str) -> int:
    try:
        return understand_jobs(int(jobs), context)
    except ValueError:
        print(f'The jobs value {jobs!r} {context} is not a valid integer.', file=sys.stderr)
        sys.exit(1)


def jobs_from_environment() -> Optional[int]:
    if "WS_JOBS" in os.environ:
        return parse_jobs(os.environ["WS_JOBS"], "passed as an Environment Variable")
    return None


def jobs_from_settings_file() -> Optional[int]:
    ws_path = Path(__file__).resolve().parent.parent.parent.resolve()
    try:
        with open(ws_path / "ws-settings.toml", "r") as settings_file:
            settings = toml.load(settings_file)
        if "jobs" in settings:
            jobs = settings["jobs"]
            if isinstance(jobs, str):
                return parse_jobs(jobs, "found in the settings file")
            if isinstance(jobs, int) and not isinstance(jobs, bool):
                return understand_jobs(jobs, "found in the settings file")
            print(
                f'The jobs setting found in the settings file has the wrong type "{type(jobs).__name__}" '
                '- please use an integer from the range [0; 1000)',
                file=sys.stderr)
            sys.exit(2)
        return None
    except FileNotFoundError:
        return None


def main():
    parser = argparse.ArgumentParser(description="Print the number of jobs that a real command would have used.")
    parser.add_argument("-j", "--jobs", metavar="JOBS", help="The number of parallel jobs to start (env: WS_JOBS)")
    args = parser.parse_args()

    jobs: Optional[int] = None
    if args.jobs is not None:
        jobs = parse_jobs(args.jobs, "passed as an Argument")

    if jobs is None:
        jobs = jobs_from_environment()

    if jobs is None:
        jobs = jobs_from_settings_file()

    if jobs is None:
        jobs = cpu_count()

    print(jobs)


main()
