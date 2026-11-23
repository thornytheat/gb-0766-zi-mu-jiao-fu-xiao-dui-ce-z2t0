import os
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge
from .modules.delivery.routes import delivery
from .modules.runs.files import CutArchive
from .modules.runs.routes import runs
from .problems import Rejection
from .web import sheets


def create_app(root=None):
    app = Flask(__name__)
    app.url_map.redirect_defaults = False
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
    app.extensions['cut_archive'] = CutArchive(root or os.getenv('CAPTION_ARCHIVE', 'var/cuts'))
    for module in (sheets, runs, delivery):
        app.register_blueprint(module)

    @app.get('/health')
    def health():
        return jsonify(status='ok')

    @app.errorhandler(Rejection)
    def error(exc):
        if request.path.startswith('/api/'):
            return jsonify(code=exc.code, message=str(exc)), exc.status
        return render_template('problem.html', message=str(exc)), exc.status

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_):
        return jsonify(code='TOO_LARGE', message='校对原件超过 2 MB'), 413

    return app
