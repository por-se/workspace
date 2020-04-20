#!/bin/sh
# This script is supposed to be run from the workspace root in the CI's dind context

set -e
set -u
set -o pipefail

set -v # print commands to CI output

# pull docker base image with token, such that the CI user does not need access to it
docker login -u $DOCKER_BASE_IMAGE_USER -p $DOCKER_BASE_IMAGE_PASSWORD laboratory.comsys.rwth-aachen.de:5050
docker build --pull --cache-from=$CI_REGISTRY_IMAGE/ci:latest -f .gitlab-ci-src/base.Dockerfile -t $CI_REGISTRY_IMAGE/ci:latest .
# log back in with the ci token
docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY

docker run --name sources -v ~/.netrc:/root/.netrc -v /cache:/cache $CI_REGISTRY_IMAGE/ci:latest bash -c "set -e ; set -u ; set -o pipefail
	cd /workspace
	cp .gitlab-ci-src/ws-settings.toml .
	PIPENV_CACHE_DIR=/cache/pipenv ./ws setup -j ${WS_JOBS} laboratory
"
docker commit \
	--change 'WORKDIR /workspace' \
	--change 'ENTRYPOINT ["/workspace/ws"]' \
	--change 'CMD ["shell", "-s", "fish"]' \
	sources $CI_REGISTRY_IMAGE/ci:$CI_COMMIT_SHA

# at this point cleanup might be performed, but we just wait for the cleanup of the dind container
