from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from app.db.models import Base
from app.db.session import build_engine


@pytest.fixture
def temp_db(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, Session


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"
