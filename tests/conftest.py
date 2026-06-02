import os
import tempfile
from pathlib import Path

import pytest

from app.database import init_db, set_db_enabled


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        monkeypatch.setenv("DATABASE_PATH", str(db_path))
        monkeypatch.setenv("POS_PATH", str(Path(__file__).resolve().parents[1] / "data" / "pos_transactions.csv"))
        # Reload DB_PATH
        import app.database as db

        db.DB_PATH = db_path
        set_db_enabled(True)
        init_db()
        yield db_path
        set_db_enabled(True)
