#!/usr/bin/env python3

import subprocess, sys, argparse, os

from pathlib import Path
from datetime import datetime, timedelta

print_run_commands = False


def run(cmd, *args, **kwargs):
    kwargs.setdefault("check", True)
    if print_run_commands:
        script_name = Path(sys.argv[0]).name
        print(f"[{script_name}]: {cmd} {args} {kwargs}")
    return subprocess.run(cmd, *args, **kwargs)


def main():
    global print_run_commands

    script_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(description="Run CI.")
    parser.add_argument(
        '--verbose',
        action='store_true',
        default=False,
        help="print verbose information (e.g., all run commands, etc.)",
    )
    parser.add_argument(
        '--dockerfile',
        type=Path,
        default=script_dir / 'Dockerfile',
        help=
        "specify Dockerfile to use as base image (default: 'Dockerfile' in script directory)"
    )
    parser.add_argument(
        '--ccache-dir',
        type=Path,
        default=None,
        help="ccache directory (get with `ccache --get-config cache_dir`)")
    parser.add_argument(
        '--cache-dir',
        type=Path,
        default=None,
        help="cache directory (e.g., `$HOME/.cache`)")
    parser.add_argument(
        '--num-threads',
        type=int,
        default=1,
        help="number of threads to use in parallel for building (default: 1)")
    parser.add_argument(
        '--release-image',
        type=str,
        default=None,
        help=
        "which phase to use for the release image (if desired): pre-build,post-build,final"
    )
    parser.add_argument(
        '--release-image-name',
        type=str,
        default=None,
        help=
        "full name for the release image (e.g., 'kleenet.comsys.rwth-aachen.de/my-project:latest')"
    )
    parser.add_argument(
        '--final-image-name',
        type=str,
        default=None,
        help=
        "full name for the final image (e.g., 'kleenet.comsys.rwth-aachen.de/my-project-ci:latest')"
    )
    args = parser.parse_args()

    # validate arguments
    if args.release_image or args.release_image_name:
        assert args.release_image and args.release_image_name, "--release-image and --release-image-name need to be specified together"

    # set global logging behavior
    print_run_commands = args.verbose

    # -- start building --

    # build base docker-image first
    do_continue = run(
        f"docker build -f {args.dockerfile} -t ci-image {script_dir.parent}".
        split(),
        check=False).returncode == 0

    # check if this is supposed to be the release-image
    if do_continue and args.release_image == "pre-build":
        do_continue = run(
            f"docker tag ci-image:latest {args.release_image_name}".split(),
            check=False).returncode == 0

    # run ./ws build
    if do_continue:
        ccache_arg = ""
        if args.ccache_dir:
            ccache_arg = f"-v {args.ccache_dir}:/ccache"

        cache_arg = ""
        if args.cache_dir:
            cache_arg = f"-v {args.cache_dir}:/cache"

        do_continue &= run(
            f"docker run --name ci-building {ccache_arg} {cache_arg} ci-image /usr/bin/bash -c"
            .split() + [f"./ws setup --git-clone-args=\"--dissociate --depth=1\" && ./ws build -j{args.num_threads}"],
            check=False).returncode == 0

    # check if this is supposed to be the release-image
    if do_continue and args.release_image == "post-build":
        do_continue = run(
            f"docker commit ci-building {args.release_image_name}".split(),
            check=False).returncode == 0

    # if the build failed, untag the release-image
    if not do_continue and args.release_image_name:
        run(f"docker rmi {args.release_image_name}".split(), check=False)

    # check if a final image is supposed to be tagged, and if so, also add an expiration date
    if args.final_image_name:
        expire_date = datetime.utcnow() + timedelta(days=1)
        expire_date_formatted = expire_date.isoformat(timespec='seconds') + 'Z'
        run([
            "docker", "commit", "--change",
            f"LABEL comsys.ExpireDate={expire_date_formatted}", "ci-building",
            args.final_image_name
        ],
            check=False)

    # remove intermediary containers & images
    run(f"docker rm ci-building".split(), check=False)
    run(f"docker rmi ci-image".split(), check=False)

    # check if building succeeded, and exit with the corresponding exit code
    retval = 0 if do_continue else 1
    sys.exit(retval)


if __name__ == "__main__":
    main()
