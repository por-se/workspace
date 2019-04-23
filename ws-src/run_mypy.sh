#!/bin/bash
set -e

if [ ! -f "./ws" ]; then
  echo >&2 "error: must be called from workspace root."
  exit 1
fi

./ws sh -c "
set -e
if ! type mypy >/dev/null 2>&1 ; then
  echo >&2 'error: mypy is not installed. Install it with \"pipenv install --dev\".'
  exit 1
fi
cd ws-src/
mypy --config-file mypy.ini workspace/"
