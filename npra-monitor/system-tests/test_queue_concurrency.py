import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

from app.db.models import ImportRun
from app.jobs.dispatcher import enqueue_run


def test_simultaneous_queue_requests_create_one_postgres_run():
    """Use an isolated temporary schema, never the app's import history."""
    url = os.getenv("NPRA_TEST_DATABASE_URL")
    if not url:
        pytest.skip("PostgreSQL integration URL not configured")
    schema = "test_queue_" + uuid.uuid4().hex
    control = create_engine(url)
    with control.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        ImportRun.__table__.create(engine)
        start = Barrier(6)

        def enqueue(_):
            with Session() as db:
                start.wait(timeout=10)
                return enqueue_run(db, trigger="UI").id

        with ThreadPoolExecutor(max_workers=6) as pool:
            ids = list(pool.map(enqueue, range(6)))
        assert len(set(ids)) == 1
        with Session() as db:
            assert db.scalar(select(func.count(ImportRun.id))) == 1
    finally:
        ImportRun.__table__.drop(engine, checkfirst=True)
        engine.dispose()
        with control.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}"'))
        control.dispose()
