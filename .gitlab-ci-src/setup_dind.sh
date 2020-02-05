# The dind server and client do not seem to be able to choose a valid default for their connection in our configuration.
export DOCKER_HOST=unix:///var/run/docker.sock
# When using dind, it's wise to use the overlayfs driver for improved performance.
# Using btrfs (at least) until https://github.com/docker/for-linux/issues/711 is fixed.
export DOCKER_DRIVER=btrfs

function kill_and_wait_for_docker {
	kill "$DOCKERD_PID"
	wait "$DOCKERD_PID"
	echo dockerd terminated gracefully
}

dockerd-entrypoint.sh >/dev/null 2>&1 &
DOCKERD_PID="$(jobs -l -p)" && echo "dockerd starting with pid $DOCKERD_PID..."

########################### room to prepare image while starting docker ###########################

# setup apk caching
mkdir -p /cache/apk
ln -s /cache/apk /etc/apk/cache

# install apk packages
apk add zstd

###################################################################################################

while if docker ps >/dev/null 2>&1 ; then false ; else true ; fi do
	echo waiting for dockerd startup...
	sleep 1
done
trap kill_and_wait_for_docker EXIT
echo started dockerd with driver "\"$DOCKER_DRIVER\""

set -v # print commands to CI output

docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
docker info

if [[ -e /cache/image.tar.zst ]] ; then
	echo "Loading image from local cache..."
	if zstd -T${WS_JOBS:-0} -d -c /cache/image.tar.zst | docker load ; then
		true # ok
	else
		echo "Local cache image corrupted - deleting..."
		rm /cache/image.tar.zst
	fi
fi
docker pull $CI_REGISTRY_IMAGE:ci || true # If we don't find a cache image, just go on without one
docker images
