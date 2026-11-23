from concurrent.futures import ThreadPoolExecutor
from app.main import create_app
from app.material import example
from app.modules.runs.files import CutArchive
from app.modules.runs.service import record


def test_repeat(client, saved):
    result = client.post(f"/api/runs/{saved['id']}/repeat").json
    assert result['reused'] and result['manifest'] == saved['manifest']


def test_restart(client, saved, tmp_path):
    again = create_app(tmp_path).test_client().get(f"/api/runs/{saved['id']}")
    assert again.json['counts']['delivered'] == '740'
    assert again.json['manifest'] == saved['manifest']


def test_bad_payload(client):
    outcome = client.post('/api/runs', json={'cues':'only'})
    assert (outcome.status_code, outcome.json['code']) == (422,'PAYLOAD')


def test_failed_cut_never_published(client):
    bad = dict(example('dirty'), cuts='')
    assert client.post('/api/runs', json=bad).status_code == 422
    assert client.get('/api/runs').json['count'] == 0


def test_parallel(tmp_path):
    archive = CutArchive(tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        items = list(pool.map(lambda _: record(archive, example('dirty')), range(4)))
    assert sum(not item['reused'] for item in items) == 1
    assert len(tuple(tmp_path.iterdir())) == 1


def test_different_files(client, saved):
    result = client.post('/api/runs', json={'sample':'clean'}).json
    assert result['id'] != saved['id']
    assert client.get('/api/runs').json['count'] == 2
