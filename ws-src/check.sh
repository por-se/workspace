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

exec ../ws /bin/bash -c "set -e ; set -u ; set -o pipefail
	cd ws-src

	# mypy
	mypy --config-file mypy.ini setup.py
	mypy --config-file mypy.ini -p workspace

	# flake8
	echo Running flake8 checks...
	flake8 --max-line-len 120 -j ${WS_JOBS:-$(nproc)} setup.py workspace

	# pylint
	pylint workspace setup.py

	# isort
	isort --check --diff -w 120 --recursive workspace setup.py \
		|| (echo && echo Imports not properly sorted - run ws-src/format.sh! && false)

	# yapf
	yapf --diff --style=.style.yapf --recursive --parallel workspace setup.py \
		|| (echo && echo Code not properly formatted - run ws-src/format.sh! && false)
"
