#!/bin/sh
# This script is supposed to be run from the workspace root in the CI's dind context

set -e
set -u
set -o pipefail

set -v # print commands to CI output

docker build --cache-from=$IMAGE_NAME:ci -f .gitlab-ci-src/base.Dockerfile -t $IMAGE_NAME:ci .
docker run --name sources -v ~/netrc:/root/.netrc -v /cache:/cache $IMAGE_NAME:ci bash -c "set -e ; set -u ; set -o pipefail
	cd /workspace
	cp .gitlab-ci-src/ws-settings.toml .
	PIPENV_CACHE_DIR=/cache/pipenv ./ws setup
"
docker commit \
	--change 'WORKDIR /workspace' \
	--change 'ENTRYPOINT ["/workspace/ws"]' \
	--change 'CMD ["shell", "-s", "fish"]' \
	sources base

# at this point cleanup might be performed, but we just wait for the cleanup of the dind container
