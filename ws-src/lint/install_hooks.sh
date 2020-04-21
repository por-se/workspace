#!/bin/bash
set -u
set -e
set -o pipefail

# adapted from https://stackoverflow.com/a/246128/65678
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
	DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
	SOURCE="$(readlink "$SOURCE")"
	[[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$(dirname "$SOURCE")" && pwd )"
cd "$DIR"

cd ../../

for hook in ws-src/lint/hooks/* ; do
	name="$(basename "${hook%.*}")"
	if [[ ! "$(readlink .git/hooks/${name})" -ef "${hook}" ]] ; then
		echo Installing "${name}" hook...
		GIT_DIR="$(git rev-parse --git-dir)"
		rm -f "${GIT_DIR}/hooks/${name}"
		ln -s ../../"${hook}" "${GIT_DIR}/hooks/${name}"
	fi
done
