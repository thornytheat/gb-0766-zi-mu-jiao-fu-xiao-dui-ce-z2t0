import pytest
from app.main import create_app
from app.material import example
from app.pipeline import inspect


@pytest.fixture
def client(tmp_path):
    return create_app(tmp_path).test_client()


@pytest.fixture
def dirty():
    return inspect(example('dirty'))


@pytest.fixture
def saved(client):
    return client.post('/api/runs', json={'sample': 'dirty'}).json
