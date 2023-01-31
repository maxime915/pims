#!/bin/bash

set -o xtrace
set -o errexit

echo "************************************** Create dependency image ******************************************"

file='./ci/version'
VERSION_NUMBER=$(<"$file")

echo "Launch Create dependency image for $VERSION_NUMBER"

docker build --rm -f scripts/docker/Dockerfile-dependencies.build -t  cytomine/pims-dependencies:$VERSION_NUMBER .

echo "Launch Create dependency image for $VERSION_NUMBER with community plugins"
PLUGIN_CSV=$(cat ./scripts/plugin-list.csv)
TAG="${VERSION_NUMBER}-community-plugins"

docker build --rm -f scripts/docker/Dockerfile-dependencies.build \
  --build-arg PLUGIN_CSV="${PLUGIN_CSV}" \
  -t cytomine/pims-dependencies:$TAG .