import connexion


def create_app():
    app = connexion.FlaskApp(__name__, specification_dir='openapi/')
    app.add_api('api-specification.yaml')

    flask_app = app.app
    return flask_app
