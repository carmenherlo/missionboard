import pytest
from fastapi.testclient import TestClient

from app.config_store import DEFAULT_PARENT_CODE
from app.main import create_app

PARENT = {"X-Parent-Code": DEFAULT_PARENT_CODE}


@pytest.fixture
def data_dir(tmp_path):
    return tmp_path / "data"


@pytest.fixture
def client(data_dir):
    with TestClient(create_app(data_dir)) as c:
        yield c
