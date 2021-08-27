#! /usr/bin/env bash

# TODO: get version from __version__.py file or version control
VERSION=0

# Build without plugin
docker build -f ../docker/Dockerfile -t cytomineuliege/pims:v${VERSION} ..

# Build with plugins
PLUGIN_CSV=$(cat ./plugin-list.csv)
docker build -f ../docker/Dockerfile \
  --build-arg PLUGIN_CSV=${PLUGIN_CSV} \
  -t cytomineuliege/pims:v${VERSION}-all-plugins
  ..
