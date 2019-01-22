#!/bin/bash
set -u
set -e
set -o pipefail

# adapted from https://stackoverflow.com/a/246128/65678
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
	DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
	SOURCE="$(readlink "$SOURCE")"
	[[ $SOURCE != /* ]] && SOURCE="$WORKSPACE/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
WORKSPACE="$( cd -P "$(dirname "$SOURCE")" && pwd )"
cd "$WORKSPACE"

export PIPENV_VENV_IN_PROJECT=1
if [[ ! -d .venv ]] ; then
	pipenv update
fi
exec pipenv run "$@"
