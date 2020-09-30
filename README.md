# pims
Python Image Management Server

## OpenAPI specification

API specification rendering using ReDoc:

    docker run -it --rm -p 18881:80 -v $(pwd):/usr/share/nginx/html/swagger/ -e SPEC_URL=swagger/api-specification.yaml -e REDOC_OPTIONS="path-in-middle-panel hide-schema-titles expand-responses=\"200,201\" json-sample-expand-level=\"3\"" redocly/redoc

Specification is then available at http://localhost:18881