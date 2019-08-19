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

cd "${DIR}/../../.."

if git status --porcelain | grep -q '^.[^ ]' ; then
	HAVE_STASHED=1
	git stash -k -u
else
	HAVE_STASHED=0
fi
function finish {
	if [[ "$HAVE_STASHED" -ne 0 ]] ; then
		git stash pop
	fi
}
trap finish EXIT

if !  ws-src/check.sh ; then
	>&2 echo
	>&2 echo "Linting failed, aborting commit..."
	exit 1
fi
