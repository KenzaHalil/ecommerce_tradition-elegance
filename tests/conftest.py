import sys
from pathlib import Path
import pytest
from datetime import datetime
import os

# s'assurer que la racine du projet est importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from run import create_app
from app import models

@pytest.fixture(scope="session")
def db_file(tmp_path_factory):
    p = tmp_path_factory.mktemp("data") / "test_elegance.db"
    return str(p)

@pytest.fixture
def app(db_file):
    config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file}",
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    }
    app = create_app(config)
    with app.app_context():
        # create_all sans ré-initialiser l'extension (create_app a déjà fait init_app)
        models.db.create_all()
    yield app
    # teardown: remove file if exists
    try:
        os.remove(db_file)
    except Exception:
        pass

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def ctx(app):
    with app.app_context():
        yield