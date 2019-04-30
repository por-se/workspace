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

../ws sh -c "
	set -u
	set -e
	set -o pipefail

	if ! type mypy >/dev/null 2>&1 ; then
	  echo >&2 'error: mypy is not installed. Install it with \"pipenv install --dev\".'
	  exit 1
	fi

	cd ws-src/
	mypy --config-file mypy.ini workspace/
"
