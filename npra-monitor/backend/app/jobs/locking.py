from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import text


class ImportAlreadyRunning(RuntimeError):
    pass


@contextmanager
def import_lock(engine, lock_key: int):
    if engine.dialect.name != "postgresql":
        # SQLite is used only for lightweight local/unit tests; a real reviewer run uses PostgreSQL.
        yield
        return
    connection = engine.connect()
    acquired = bool(connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": lock_key}).scalar())
    if not acquired:
        connection.close()
        raise ImportAlreadyRunning("another import holds the NPRA advisory lock")
    try:
        yield
    finally:
        try:
            connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": lock_key})
        finally:
            connection.close()
