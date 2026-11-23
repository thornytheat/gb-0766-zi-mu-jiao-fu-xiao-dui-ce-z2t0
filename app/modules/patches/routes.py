from flask import Blueprint, current_app, jsonify, request
from app.modules.delivery.service import CODES
from app.problems import Rejection
from .checks import verify_patch
from .ledger import REASON_LABELS
from .service import apply_patch, patch_summary

patches = Blueprint('patches', __name__, url_prefix='/api/patches')


def stores():
    return current_app.extensions['cut_archive'], current_app.extensions['patch_archive']


def require_patch(key):
    record = stores()[1].read(key)
    if record['manifest'].get('kind') != 'patch':
        raise Rejection('NO_PATCH', '补丁档案不存在', 404)
    return record


@patches.get('')
def index():
    _, patch_store = stores()
    rows = []
    for path in patch_store.root.glob('*.json'):
        entry = patch_store.read(path.stem)
        if entry['manifest'].get('kind') == 'patch':
            rows.append(entry['manifest'])
    rows.sort(key=lambda row: (row['created_at'], row['id']), reverse=True)
    return jsonify(count=len(rows), rows=rows)


@patches.post('')
def publish():
    master_store, patch_store = stores()
    return jsonify(apply_patch(master_store, patch_store, request.get_json(silent=True)))


@patches.get('/<key>')
def detail(key):
    return jsonify(patch_summary(require_patch(key)))


@patches.get('/<key>/landing')
def landing_view(key):
    return jsonify(require_patch(key)['stages']['patches'])


@patches.get('/<key>/certificate')
def certificate(key):
    return jsonify(verified=True, certificate=verify_patch(require_patch(key)))


@patches.get('/<key>/export')
def export(key):
    record = require_patch(key)
    payload = dict(verified=True, certificate=verify_patch(record), **record,
                   reason_codes={**CODES, **REASON_LABELS})
    response = jsonify(payload)
    response.headers['Content-Disposition'] = f'attachment; filename="caption-patch-{key}.json"'
    return response
