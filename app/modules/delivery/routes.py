from flask import Blueprint, jsonify
from app.modules.runs.routes import archive
from .checks import verify
from .service import signing

delivery = Blueprint('delivery', __name__)


@delivery.get('/api/delivery/<key>')
def certificate(key):
    return jsonify(verified=True, certificate=verify(archive().read(key)))


@delivery.get('/api/delivery/<key>/export')
def export(key):
    response = jsonify(signing(archive().read(key)))
    response.headers['Content-Disposition'] = f'attachment; filename="caption-proof-{key}.json"'
    return response
