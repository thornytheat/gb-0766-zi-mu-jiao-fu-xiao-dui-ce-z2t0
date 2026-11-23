def test_clean_clip_api(client):
    result = client.get('/api/check/balance?sample=clean')
    assert result.json['counts']['delivered'] == '290'


def test_out_of_catalog(client):
    result = client.get('/api/check/source?sample=missing')
    assert (result.status_code, result.json['code']) == (404, 'NO_SAMPLE')


def test_clock_runs_without_valid_cut_table(client):
    from app.material import example
    files = dict(example('dirty'), cuts='')
    assert client.post('/api/check/clock', json=files).json['counts'] == dict(valid=15, isolated=1)
    assert client.post('/api/check/edits', json=files).json['code'] == 'EMPTY'
    assert client.get('/api/runs').json['count'] == 0
