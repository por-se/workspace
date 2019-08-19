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

exec ../ws /bin/bash -c 'set -e ; set -u ; set -o pipefail
	cd ws-src
	JOBS="$(lint/jobs.py)"

	# isort
	echo Sorting imports with isort...
	isort -j "$JOBS" --apply -w 120 --recursive lint/jobs.py setup.py workspace

	# yapf
	echo Formatting code with yapf...
	yapf --in-place --style=.style.yapf --recursive --parallel lint/jobs.py setup.py workspace
'
