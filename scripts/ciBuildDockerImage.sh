#!/bin/bash

set -o xtrace
set -o errexit

echo "************************************** Publish docker (PIMS without plugins) ******************************************"

file='./ci/version'
VERSION_NUMBER=$(<"$file")
echo $VERSION_NUMBER
docker build --rm -f ./scripts/docker/Dockerfile-final.build \
  --build-arg VERSION_NUMBER=$VERSION_NUMBER \
  --build-arg TAG=$VERSION_NUMBER \
  -t  cytomine/pims:$VERSION_NUMBER ./

docker push cytomine/pims:$VERSION_NUMBER

docker rmi cytomine/pims:$VERSION_NUMBER
docker rmi cytomine/pims-dependencies:$VERSION_NUMBER

echo "************************************** Publish docker (PIMS with plugins) ******************************************"
PLUGIN_CSV=$(cat ./scripts/plugin-list.csv)
TAG="${VERSION_NUMBER}-community-plugins"
echo $TAG
docker build --rm -f ./scripts/docker/Dockerfile-final.build \
  --build-arg VERSION_NUMBER=$VERSION_NUMBER \
  --build-arg TAG=$TAG \
  -t  cytomine/pims:$TAG ./

docker push cytomine/pims:$TAG

docker rmi cytomine/pims:$TAG
docker rmi cytomine/pims-dependencies:$TAG
