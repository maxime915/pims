# pims
Python Image Management Server

## Run development server

    export FLASK_APP=pims/app.py
    flask run

The server is running at http://127.0.0.1:5000

## OpenAPI specification

The OpenAPI specification is in `pims/openapi`. The [Connexion](https://github.com/zalando/connexion) framework is
 used on top of Flask for automatic endpoint validation from the specification.
 
The specification is rendered with ReDoc and available at http://127.0.0.1:5000/docs
