#!/bin/sh
# This script is supposed to be run from the workspace root in the CI's dind context

set -e
set -u
set -o pipefail

docker build --cache-from=$IMAGE_NAME:ci -f .gitlab-ci-src/base.Dockerfile -t base .
docker run --name sources -v ~/netrc:/root/netrc base bash -c "set -e ; set -u ; set -o pipefail
	cp .gitlab-ci-src/ws-settings.toml .
	./ws setup
"
docker commit --change "CMD bash" sources $IMAGE_NAME:ci

# at this point cleanup might be performed, but we just wait for the cleanup of the dind container