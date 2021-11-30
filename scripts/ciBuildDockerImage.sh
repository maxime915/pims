#!/bin/bash

set -o xtrace
set -o errexit

echo "************************************** Publish docker ******************************************"

file='./ci/version'
VERSION_NUMBER=$(<"$file")

docker build --rm -f ./scripts/docker/Dockerfile-final.build --build-arg VERSION_NUMBER=$VERSION_NUMBER -t  cytomine/pims:v$VERSION_NUMBER ./

docker push cytomine/pims:v$VERSION_NUMBER

docker rmi cytomine/pims:v$VERSION_NUMBER
docker rmi cytomine/pims-dependencies:v$VERSION_NUMBER