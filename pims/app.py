import connexion


def create_app():
    app = connexion.FlaskApp(__name__, specification_dir='openapi/')
    api = app.add_api('api-specification.yaml')
    flask_app = app.app

    flask_app.config['api_version'] = api.specification.raw['info']['version']

    return flask_app
