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

def setup_and_parse_args():
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
        "which phase to use for the release image (if desired): pre-build,post-build,final. See --release-image-name for more information."
    )
    parser.add_argument(
        '--release-image-name',
        type=str,
        default=None,
        help=
        "full name for the release image. This image is only tagged if all stages (e.g., build, test, etc.) succeeded, and will not have an expiration date. (e.g., 'kleenet.comsys.rwth-aachen.de/my-project:latest')"
    )
    parser.add_argument(
        '--final-image-name',
        type=str,
        default=None,
        help=
        "full name for the final image. This image is always tagged (if a container could be created), and will contain the final state of the CI-process. This image will also have an expiration date. (e.g., 'kleenet.comsys.rwth-aachen.de/my-project-ci:latest')"
    )

    args = parser.parse_args()

    # validate arguments
    if args.release_image or args.release_image_name:
        assert args.release_image and args.release_image_name, "--release-image and --release-image-name need to be specified together"

    return args


def main():
    global print_run_commands

    args = setup_and_parse_args()

    # set global logging behavior
    print_run_commands = args.verbose

    # -- build --
    build_success = True
    try:
        # build base docker-image first
        run(["docker", "build", "-f", str(args.dockerfile), "-t", "ci-image", str(script_dir.parent)])

        # check if this is supposed to be the release-image
        if args.release_image == "pre-build":
            run(["docker", "tag", "ci-image:latest", str(args.release_image_name)])

        # run ./ws build
        ccache_arg = ["-v", f"{args.ccache_dir}:/ccache"] if args.ccache_dir else []
        cache_arg = ["-v", f"{args.cache_dir}:/cache"] if args.cache_dir else []
        run(["docker", "run", "--name", "ci-building"] + ccache_arg + cache_arg + ["ci-image", "/usr/bin/bash", "-c",
            f"./ws setup --git-clone-args=\"--dissociate --depth=1 -c pack.threads={args.num_threads}\" && ./ws build -j{args.num_threads}"])

        # check if this is supposed to be the release-image
        if args.release_image == "post-build":
            run(["docker", "commit", "ci-building", str(args.release_image_name)])

    except subprocess.CalledProcessError:
        build_success = False

        # if the build failed, untag the release-image
        run(["docker", "rmi", str(args.release_image_name)], check=False)

    # check if a final image is supposed to be tagged, and if so, also add an expiration date
    if args.final_image_name:
        expire_date = datetime.utcnow() + timedelta(days=1)
        expire_date_formatted = expire_date.isoformat(timespec='seconds') + 'Z'
        run(["docker", "commit", "--change", f"LABEL comsys.ExpireDate={expire_date_formatted}", "ci-building", args.final_image_name], check=False)

    # remove intermediary containers & images
    run(["docker", "rm", "ci-building"], check=False)
    run(["docker", "rmi", "ci-image"], check=False)

    # check if building succeeded, and exit with the corresponding exit code
    sys.exit(0 if build_success else 1)


if __name__ == "__main__":
    main()
