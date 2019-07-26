#!/usr/bin/env python3

import subprocess, sys, argparse, os, tempfile

from pathlib import Path
from datetime import datetime, timedelta

print_run_commands = False
script_dir = Path(__file__).resolve().parent


def run(cmd, *args, **kwargs):
    kwargs.setdefault("check", True)
    if print_run_commands:
        script_name = Path(sys.argv[0]).name
        print(f"[{script_name}]: {cmd} {args} {kwargs}")
    return subprocess.run(cmd, *args, **kwargs)

def setup_and_parse_args():
    global script_dir

    parser = argparse.ArgumentParser(description="Run CI.")
    parser.add_argument(
        '--verbose',
        action='store_true',
        default=False,
        help="print verbose information (e.g., all run commands, etc.)",
    )
    parser.add_argument(
        '--forward-gitlab-ci-token',
        action='store_true',
        default=False,
        help="forward the gitlab ci-token to command being executed inside the docker container. this is for example required when gitlab-local repositories are cloned as part of the build (inside the container).",
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
    global print_run_commands, script_dir

    args = setup_and_parse_args()

    # set global logging behavior
    print_run_commands = args.verbose

    # -- build --
    build_success = True
    try:
        # build base docker-image first
        run(["docker", "build", "-f", str(args.dockerfile), "-t", "ci-image", str(script_dir.parent)])

        # helper function to run a command with options in the docker container and to commit the result
        def docker_run_and_commit(run_options, command, commit_options=[], check=True):
            run(["docker", "run", "--name", "ci-temp"] + run_options + ["ci-image:latest"] + command, check=check)
            run(["docker", "commit"] + commit_options + ["ci-temp", "ci-image:latest"], check=check)
            run(["docker", "rm", "ci-temp"], check=check)

        # check if this is supposed to be the release-image
        if args.release_image == "pre-build":
            run(["docker", "tag", "ci-image:latest", str(args.release_image_name)])

        # if requested, forward the gitlab-ci-token by writing it to a file that we mount into the container
        gitlab_ci_token_args = []
        ci_token_temp_dir = None
        if args.forward_gitlab_ci_token:
            token = os.environ['CI_JOB_TOKEN']
            ci_token_temp_dir = tempfile.TemporaryDirectory() # will be cleaned up by the destructor when the script exits (or sooner)
            with open(Path(ci_token_temp_dir.name) / 'netrc', "w") as f:
                f.write(f"machine laboratory.comsys.rwth-aachen.de\nlogin gitlab-ci-token\npassword {token}\n")
            gitlab_ci_token_args = ["-v", f"{ci_token_temp_dir.name}:/ci-token-dir"]

        # run ./ws build
        ccache_arg = ["-v", f"{args.ccache_dir}:/ccache"] if args.ccache_dir else []
        cache_arg = ["-v", f"{args.cache_dir}:/cache"] if args.cache_dir else []
        docker_run_and_commit(run_options = ccache_arg + cache_arg + gitlab_ci_token_args,
            command = ["/usr/bin/bash", "-c",
            f"""set -e ; set -u ; set -o pipefail
            export PATH=\"/usr/share/git/credential/netrc:$PATH\"
            export WS_JOBS={args.num_threads}
            git config --global credential.helper 'netrc -k -v -f /ci-token-dir/netrc'
            ./ws setup --reference-repositories=/cache/reference-repos --X-git-clone=--dissociate --X-git-clone=--depth=1
            ./ws build
            git config --global --unset credential.helper"""])

        # check if this is supposed to be the release-image
        if args.release_image == "post-build":
            run(["docker", "tag", "ci-image:latest", str(args.release_image_name)])

    except subprocess.CalledProcessError:
        build_success = False

        # if the build failed, untag the release-image
        run(["docker", "rmi", str(args.release_image_name)], check=False)

    # check if a final image is supposed to be tagged, and if so, also add an expiration date
    if args.final_image_name:
        expire_date = datetime.utcnow() + timedelta(days=1)
        expire_date_formatted = expire_date.isoformat(timespec='seconds') + 'Z'
        docker_run_and_commit(run_options=[], command=["/usr/bin/bash", "-c", "exit"], commit_options=["--change", f"LABEL comsys.ExpireDate={expire_date_formatted}"], check=False)
        run(["docker", "tag", "ci-image:latest", str(args.final_image_name)], check=False)

    # remove intermediary containers & images
    run(["docker", "rm", "ci-temp"], check=False)
    run(["docker", "rmi", "ci-image"], check=False)

    # check if building succeeded, and exit with the corresponding exit code
    sys.exit(0 if build_success else 1)


if __name__ == "__main__":
    main()
