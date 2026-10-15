"""
CARspective — Database Infrastructure
SQLAlchemy 2.0 Engine & Scoped Session Factory
Application-level schema parity with database-specific type handling and connection reliability.
"""

from typing import Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.engine import Engine
from server.config import settings
from server.config.settings import normalize_database_url, mask_database_url
from server.models.base import Base

normalized_db_url = normalize_database_url(settings.DATABASE_URL)
is_sqlite = normalized_db_url.startswith("sqlite")

engine_kwargs = {
    "echo": False,
    "future": True,
    "pool_pre_ping": True,
}

if is_sqlite:
    engine_kwargs["connect_args"] = {
        "check_same_thread": False,
        "timeout": 30.0,
    }
else:
    # Server-class database settings (PostgreSQL, MySQL, etc.)
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 1800,
        "pool_timeout": 30.0,
    })

engine = create_engine(
    normalized_db_url,
    **engine_kwargs
)

# Enable foreign keys, busy timeout, and WAL journal mode for SQLite
if is_sqlite:
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        if ":memory:" not in settings.DATABASE_URL:
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
            except Exception:
                pass
        cursor.close()

SessionFactory = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True
)

ScopedSession = scoped_session(SessionFactory)


def get_db() -> Generator[Session, None, None]:
    """Dependency provider yielding a scoped database session."""
    session = ScopedSession()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def transaction_scope(session: Session = None) -> Generator[Session, None, None]:
    """
    Provide a transactional boundary around a series of operations.
    Commits automatically on clean block completion, rolls back on exception.
    """
    sess = session or ScopedSession()
    is_internal_session = (session is None)
    try:
        yield sess
        sess.commit()
    except Exception:
        sess.rollback()
        raise
    finally:
        if is_internal_session:
            sess.close()


def dispose_engine(target_engine=None) -> None:
    """Explicitly dispose the connection pool and release underlying socket/file handles."""
    eng = target_engine or engine
    if eng is not None:
        eng.dispose()


def init_db(target_engine=None) -> None:
    """Create all declarative tables in the target database (development/test helper)."""
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)


def drop_db(target_engine=None) -> None:
    """Drop all tables (primarily for isolated test fixtures)."""
    eng = target_engine or engine
    Base.metadata.drop_all(bind=eng)
