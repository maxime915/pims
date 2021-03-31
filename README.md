# pims
Python Image Management Server

## Run development server with Docker

    docker build -f docker/Dockerfile -t pims .
    docker run -p 5000:5000 pims

The server is running at http://127.0.0.1:5000

## Run development server locally 
Dependencies in Dockerfile must be installed first.

    export FLASK_APP=pims/app.py
    flask run


## OpenAPI specification

The OpenAPI specification is in `pims/openapi`. 
 
The specification is rendered with ReDoc and available at http://127.0.0.1:5000/docs
