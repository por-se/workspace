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
if [[ ! -d .venv ]] || [[ Pipfile.lock -nt .venv ]] ; then
	if [[ -r /etc/issue ]] && [[ "$(cat /etc/issue)" = 'Debian'* ]] ; then
		# https://github.com/pypa/pipenv/issues/1744
		>&2 echo "Performing workaround for Debian"
		pushd ws-src
		pipenv run python setup.py develop
		popd
	fi
	pipenv sync
	touch .venv
fi
exec pipenv run "$@"
