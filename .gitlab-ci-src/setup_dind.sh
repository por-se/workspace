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

apk add zstd

###################################################################################################

while if docker ps >/dev/null 2>&1 ; then false ; else true ; fi do
	echo waiting for dockerd startup...
	sleep 1
done
trap kill_and_wait_for_docker EXIT
echo started dockerd with driver "\"$DOCKER_DRIVER\""

docker login -u "$DOCKER_CI_USER" -p "$DOCKER_CI_AUTH" $DOCKER_REGISTRY
docker info

DOCKER_SAVE=false
if [[ -e /cache/image.tar.zst ]] ; then
	echo "Loading image from local cache..."
	zstd -d -c /cache/image.tar.zst | docker load
	docker pull $IMAGE_NAME:latest || true
	if [[ "$(docker images | wc -l)" -eq 3 ]] ; then
		DOCKER_SAVE=true
	fi
else
	if docker pull $IMAGE_NAME:latest ; then
		DOCKER_SAVE=true
	fi
fi
docker images