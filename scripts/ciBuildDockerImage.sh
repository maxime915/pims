#!/bin/bash

set -o xtrace
set -o errexit

echo "************************************** Publish docker ******************************************"

file='./ci/version'
VERSION_NUMBER=$(<"$file")
echo $VERSION_NUMBER
docker build --rm -f ./scripts/docker/Dockerfile-final.build -t  cytomine/pims:v$VERSION_NUMBER --build-arg VERSION_NUMBER=$VERSION_NUMBER ./

docker push cytomine/pims:$VERSION_NUMBER

docker rmi cytomine/pims:$VERSION_NUMBER
docker rmi cytomine/pims-dependencies:$VERSION_NUMBER