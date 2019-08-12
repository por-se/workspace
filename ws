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
if [[ ! -d .venv ]] || [[ Pipfile.lock -nt .venv ]] || not pipenv run run echo >/dev/null 2>&1 ; then
	rm -rf .venv
	if [[ -r /etc/issue ]] && [[ "$(cat /etc/issue)" = 'Debian'* ]] ; then
		# https://github.com/pypa/pipenv/issues/1744
		>&2 echo "Performing workaround for Debian"
		pushd ws-src
		pipenv run python setup.py develop
		popd
	fi
	if pipenv sync && [[ -d .venv ]] ; then
		touch .venv
	else
		if [[ -e Pipfile.lock ]] ; then
			rm -rf .venv
		else
			>&2 echo Missing Pipfile.lock: run `git checkout -- Pipfile.lock` or `pipenv lock`.
		fi
		>&2 echo Failed to synchronize virtualenv
		exit 1
	fi
fi
exec pipenv run "$@"
