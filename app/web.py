from flask import Blueprint, jsonify, render_template, request
from .grid_view import HEADERS, LABELS, cells
from .material import example, material
from .modules.delivery.checks import verify
from .modules.delivery.service import CODES
from .modules.runs.routes import archive
from .pipeline import inspect
from .problems import Rejection

sheets = Blueprint('sheets', __name__)
TABS = {'source': '文件采信', 'clock': '帧率校核', 'edits': '切版映射', 'overlaps': '冲突定位',
        'balance': '覆盖对账', 'runs': '版本归档', 'delivery': '交付签发'}


def current():
    key = request.args.get('run')
    name = request.args.get('sample', 'dirty')
    if key:
        entry = archive().read(key)
        return entry['stages'], entry['manifest'], name
    return inspect(example(name)), None, name


@sheets.get('/api/check/<sheet>')
def data(sheet):
    if sheet not in tuple(TABS)[:5]:
        raise Rejection('NO_SHEET', '未找到校对页', 404)
    key = request.args.get('run')
    if key:
        return jsonify(archive().read(key)['stages'][sheet])
    return jsonify(inspect(example(request.args.get('sample', 'dirty')), until=sheet))


@sheets.post('/api/check/<sheet>')
def check_originals(sheet):
    if sheet not in tuple(TABS)[:5]:
        raise Rejection('NO_SHEET', '未找到校对页', 404)
    return jsonify(inspect(material(request.get_json(silent=True)), until=sheet))


@sheets.get('/', defaults={'sheet': 'edits'})
@sheets.get('/sheet/<sheet>')
def grid(sheet):
    if sheet not in TABS:
        raise Rejection('NO_SHEET', '未找到校对页', 404)
    stages, manifest, sample = current()
    if sheet == 'delivery' and manifest:
        verify(archive().read(manifest['id']))
    return render_template('workbook.html', sheet=sheet, tabs=TABS, sample=sample, manifest=manifest,
                           totals=stages['balance']['counts'], rows=cells(stages, sheet, archive(), manifest),
                           columns=HEADERS[sheet], labels=LABELS, codes=CODES)
