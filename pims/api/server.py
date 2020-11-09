from flask import current_app

from pims import __version__


def show_status():
    return {
        'version': __version__,
        'api_version': current_app.config['api_version']
    }
