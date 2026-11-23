import pytest
from app.modules.delivery.service import signing
from app.problems import Rejection


def test_download(client, saved):
    response = client.get(f"/api/delivery/{saved['id']}/export")
    assert 'attachment;' in response.headers['Content-Disposition']
    assert response.json['original']['cues'].startswith('\ufefflegacy_id')


def test_archive_stamp(client, saved):
    assert client.get(f"/api/delivery/{saved['id']}").json['certificate'] == saved['manifest']


def test_unknown_delivery(client):
    assert client.get('/api/delivery/none/export').json['code'] == 'NO_RUN'


def test_mutated_original(client, saved):
    entry = client.application.extensions['cut_archive'].read(saved['id'])
    entry['original']['cuts'] += '\n'
    with pytest.raises(Rejection, match='证据散列'):
        signing(entry)


def test_mutated_result(client, saved):
    entry = client.application.extensions['cut_archive'].read(saved['id'])
    entry['stages']['overlaps']['rows'].clear()
    with pytest.raises(Rejection, match='证据散列'):
        signing(entry)


def test_precision_survives_roundtrip(client, saved):
    response = client.get(f"/api/delivery/{saved['id']}/export").json
    assert response['stages']['overlaps']['rows'][-1]['cues'][0] == '9007199254740993'
