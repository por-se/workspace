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

exec ../../ws isort -j ${WS_JOBS:-$(nproc)} --check --diff -w 120 --recursive ws-src/workspace ws-src/setup.py
