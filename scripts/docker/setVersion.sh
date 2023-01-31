#!/bin/bash -x

# Replace the version /__version__.py with the one extracted from GIT TAG

echo "Parameter $1"

if [[ $gitLongTag =~ v[0-9]+.[0-9]+.[0-9]+-beta.[0-9]+-0-[0-9a-g]{8,9}$ ]]; then
    echo "beta release"
elif [[ "$1" =~ [0-9]+.[0-9]+.[0-9]+$ ]]; then
    echo "Official release"
else
    echo "Release candidates"
fi

sed -i -- 's/__version__ = "0.0.0"/__version__ = "'$1'"/g' /app/pims/__version__.py ;


cat /app/pims/__version__.py


