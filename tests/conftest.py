import pytest

from lmmock.app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path)
