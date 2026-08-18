import os
import shutil
import pytest

from app import create_app, db
from config import TestConfig


@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app
    shutil.rmtree(TestConfig.STORAGE_DIR, ignore_errors=True)


@pytest.fixture
def client(app):
    return app.test_client()
