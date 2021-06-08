# pims
Python Image Management Server

## Run development server with Docker

    docker build -f docker/Dockerfile -t pims .
    docker run -p 5000:5000 pims

The server is running at http://127.0.0.1:5000

## Run development server locally 
First, dependencies must be installed
1. Dependencies in Dockerfile must be installed first.
2. `pip install -r requirements.txt`

To run the development server, run:
```bash
CONFIG_FILE="/path/to/my/config.env" python -m pims.main
```
    
The server is running at http://127.0.0.1:5000

### Environment variables
* `CONFIG_FILE`: path to a `.env` configuration file. Default to `pims-config.env` (but some required configuration 
  settings need to be filled)
* `LOG_CONFIG_FILE`: path to a `.yml` Python logging configuration file. Default to `logging.yml`
* `DEBUG`: When set, enable debug tools and use `logging-debug.yml` as default logging configuration if not other 
  log config file is specified.
  
Configuration settings can be also given as environment variables and override values from `CONFIG_FILE`.
