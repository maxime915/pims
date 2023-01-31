# PIMS Build & Continous integration

## Jenkins file

A `Jenkinsfile` is located at the root of the directory.
Build steps:
* Clean `./ci` directory ; In this directory we will store all temp data for the build.
* Get the current version (see Versionning section)
* Create a Docker image with all dependencies. The "test" and "final release" Docker images will both be defined from the image.
* Run tests 
* Build the final release as a docker image
* Push the final release on dockerhub

The `scripts/ciBuildLocal.sh` contains same steps as Jenkinsfile but can be run without Jenkins.

## Tests

Tests are run with pytest.
The test report is extracted as a XML file in `ci/test-reports`

## Final build

The final image is pushed on dockerhub (https://hub.docker.com/r/cytomine/pims)

## Versioning

The version stored in the repository must always be 0.0.0

    VERSION = (0, 0, 0)

A script will replace this version during the build if the current commit tag match the pattern 

    v[0-9]+.[0-9]+.[0-9]

The docker image pushed on dockerhub will be tagged with this version number.

Example: if the current commit has this tag `v1.2.3`, the `__version__.py` contains this in the release:

    VERSION = (1, 2, 3)

The docker image will be available thanks to `docker pull cytomine/pims:v1.2.3` 

If the current commit does not correspond to a v'x.y.z' release, it will get the value:

`v$branchName-$datetime-SNAPSHOT` 

In this case, the docker image will be something like `cytomine/pims:vNice-feature-20210101161510-SNAPSHOT`
